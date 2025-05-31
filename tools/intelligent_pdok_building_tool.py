import math
import requests
import re
from datetime import datetime
from smolagents import Tool
from typing import Dict, List, Optional, Tuple

class IntelligentPDOKBuildingTool(Tool):
    """
    Intelligent PDOK Buildings tool that adapts search radius and strategy based on query context.
    
    Features:
    - Context-aware radius calculation (city vs street address vs specific location)
    - Intelligent building density estimation
    - Progressive radius expansion if insufficient results
    - Always starts from specified location and expands outward
    - Adapts strategy based on query type and user intent
    """
    
    name = "get_buildings_intelligent"
    description = "Get buildings with intelligent radius calculation and context-aware search strategy based on location type and user intent"
    inputs = {
        "location": {"type": "string", "description": "Location (e.g., 'Groningen', 'Kloosterstraat 27 Ten Boer', 'Amsterdam train station')"},
        "max_features": {"type": "integer", "description": "Number of buildings wanted (agent calculates appropriate radius)", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "search_strategy": {"type": "string", "description": "Search strategy: 'nearest' (default), 'random', 'historic_priority'", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
        
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            print("✅ Intelligent PDOK tool initialized with coordinate transformers")
        except ImportError:
            print("❌ PyProj required for intelligent PDOK tool")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, location, max_features=10, min_year=None, max_year=None, search_strategy="nearest"):
        """Intelligent building search with context-aware radius calculation."""
        
        try:
            print(f"\n🧠 === INTELLIGENT PDOK BUILDING SEARCH ===")
            print(f"Location: {location}")
            print(f"Requested buildings: {max_features}")
            print(f"Strategy: {search_strategy}")
            
            # Step 1: Enhanced location analysis
            location_context = self._analyze_location_context(location)
            print(f"📍 Location type: {location_context['type']}")
            print(f"🎯 Suggested strategy: {location_context['strategy']}")
            
            # Step 2: Get precise coordinates
            from tools.pdok_location import find_location_coordinates
            loc_data = find_location_coordinates(location)
            
            if "error" in loc_data:
                return {
                    "text_description": f"❌ Could not find location: {location}. {loc_data['error']}",
                    "geojson_data": [],
                    "error": loc_data["error"]
                }
            
            target_lat, target_lon = loc_data["lat"], loc_data["lon"]
            print(f"✅ Coordinates: {target_lat:.6f}, {target_lon:.6f}")
            
            # Step 3: Calculate intelligent initial radius
            initial_radius = self._calculate_intelligent_radius(
                location_context, max_features, min_year, max_year
            )
            print(f"🧮 Initial search radius: {initial_radius}km")
            
            # Step 4: Progressive search with radius expansion if needed
            all_buildings = []
            current_radius = initial_radius
            max_radius = location_context.get('max_radius', 20.0)
            attempts = 0
            
            while len(all_buildings) < max_features and current_radius <= max_radius and attempts < 4:
                attempts += 1
                print(f"\n🔍 Search attempt {attempts}: radius {current_radius:.1f}km")
                
                # Get buildings for current radius
                buildings = self._search_buildings_at_radius(
                    target_lat, target_lon, current_radius, 
                    max_features * 3,  # Get more candidates
                    min_year, max_year
                )
                
                if buildings:
                    # Calculate distances and sort by proximity
                    buildings_with_distance = []
                    for building in buildings:
                        distance = self._calculate_distance_km(
                            target_lat, target_lon,
                            building.get('lat', 0), building.get('lon', 0)
                        )
                        building['distance_km'] = distance
                        buildings_with_distance.append(building)
                    
                    # Sort by distance (nearest first) - THIS IS KEY!
                    buildings_with_distance.sort(key=lambda x: x['distance_km'])
                    
                    # Filter to unique buildings not already found
                    for building in buildings_with_distance:
                        building_id = building.get('properties', {}).get('identificatie')
                        if building_id and not any(b.get('properties', {}).get('identificatie') == building_id for b in all_buildings):
                            all_buildings.append(building)
                    
                    print(f"📦 Found {len(buildings)} buildings, total unique: {len(all_buildings)}")
                    
                    # Show closest buildings found
                    for i, building in enumerate(all_buildings[:3]):
                        dist = building.get('distance_km', 0)
                        year = building.get('properties', {}).get('bouwjaar', 'Unknown')
                        print(f"   {i+1}. Distance: {dist:.3f}km, Year: {year}")
                
                if len(all_buildings) >= max_features:
                    print(f"✅ Found enough buildings ({len(all_buildings)}) within {current_radius:.1f}km")
                    break
                
                # Expand radius using intelligent progression
                if location_context['type'] == 'specific_address':
                    current_radius *= 1.5  # Smaller expansion for addresses
                elif location_context['type'] == 'city':
                    current_radius *= 2.0  # Larger expansion for cities
                else:
                    current_radius *= 1.8  # Medium expansion for other types
                
                print(f"🔄 Expanding radius to {current_radius:.1f}km")
            
            # Step 5: Apply search strategy and limit results
            final_buildings = self._apply_search_strategy(
                all_buildings, max_features, search_strategy, target_lat, target_lon
            )
            
            if not final_buildings:
                return {
                    "text_description": f"❌ No buildings found near {location} matching your criteria. Searched up to {current_radius:.1f}km radius.",
                    "geojson_data": [],
                    "error": "No buildings found"
                }
            
            # Step 6: Create enhanced response
            text_description = self._create_intelligent_description(
                final_buildings, location, loc_data, location_context, 
                search_strategy, max_features, min_year, max_year
            )
            
            print(f"🎉 Returning {len(final_buildings)} buildings using {search_strategy} strategy")
            
            return {
                "text_description": text_description,
                "geojson_data": final_buildings
            }
            
        except Exception as e:
            error_msg = f"Intelligent PDOK tool error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error retrieving buildings near {location}: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _analyze_location_context(self, location: str) -> Dict:
        """Analyze location to determine search context and strategy."""
        location_lower = location.lower()
        
        # Check for specific address patterns
        address_patterns = [
            r'\d+.*\w+straat',  # "27 Kloosterstraat"  
            r'\w+straat\s+\d+',  # "Kloosterstraat 27"
            r'\w+weg\s+\d+',     # "Hoofdweg 123"
            r'\w+laan\s+\d+',    # "Parklaan 45"
            r'\w+plein\s+\d+',   # "Marktplein 12"
        ]
        
        is_specific_address = any(re.search(pattern, location_lower) for pattern in address_patterns)
        
        # Check for train stations
        is_train_station = any(term in location_lower for term in [
            'station', 'centraal', 'cs', 'train'
        ])
        
        # Check for major cities
        major_cities = [
            'amsterdam', 'rotterdam', 'den haag', 'the hague', 'utrecht', 
            'eindhoven', 'tilburg', 'groningen', 'almere', 'breda'
        ]
        is_major_city = any(city in location_lower for city in major_cities)
        
        # Check for historic search intent
        is_historic_search = any(term in location_lower for term in [
            'historic', 'old', 'ancient', 'medieval', 'centrum', 'binnenstad'
        ])
        
        # Determine location type and strategy
        if is_specific_address:
            return {
                'type': 'specific_address',
                'strategy': 'nearest',
                'initial_radius': 0.5,  # 500m
                'expansion_factor': 1.5,
                'max_radius': 5.0,
                'density_estimate': 'high',
                'description': 'specific street address'
            }
        
        elif is_train_station:
            return {
                'type': 'transport_hub',
                'strategy': 'nearest',
                'initial_radius': 1.0,  # 1km
                'expansion_factor': 1.8,
                'max_radius': 10.0,
                'density_estimate': 'very_high',
                'description': 'train station area'
            }
        
        elif is_major_city:
            return {
                'type': 'city',
                'strategy': 'historic_priority' if is_historic_search else 'diverse_sample',
                'initial_radius': 5.0,  # 5km for city center
                'expansion_factor': 2.0,
                'max_radius': 25.0,
                'density_estimate': 'medium',
                'description': 'major city'
            }
        
        else:
            return {
                'type': 'general_location',
                'strategy': 'nearest',
                'initial_radius': 2.0,  # 2km
                'expansion_factor': 1.8,
                'max_radius': 15.0,
                'density_estimate': 'medium',
                'description': 'general location'
            }
    
    def _calculate_intelligent_radius(self, location_context: Dict, max_features: int, 
                                    min_year: Optional[int], max_year: Optional[int]) -> float:
        """Calculate intelligent initial radius based on context and requirements."""
        
        base_radius = location_context['initial_radius']
        
        # Adjust for number of buildings requested
        if max_features <= 5:
            feature_factor = 0.8
        elif max_features <= 10:
            feature_factor = 1.0
        elif max_features <= 20:
            feature_factor = 1.5
        else:
            feature_factor = 2.0
        
        # Adjust for historic buildings (they're rarer)
        age_factor = 1.0
        if max_year and max_year < 1950:
            age_factor = 2.0  # Historic buildings need larger search area
            print(f"🏛️ Historic building search detected - expanding radius factor to {age_factor}x")
        elif max_year and max_year < 1900:
            age_factor = 3.0  # Very old buildings are very rare
            print(f"🏺 Very old building search detected - expanding radius factor to {age_factor}x")
        
        # Adjust for location density estimate
        density_factors = {
            'very_high': 0.7,  # Dense areas like train stations
            'high': 0.8,       # Urban addresses
            'medium': 1.0,     # Regular areas
            'low': 1.5         # Rural areas
        }
        
        density_factor = density_factors.get(location_context['density_estimate'], 1.0)
        
        # Calculate final radius
        calculated_radius = base_radius * feature_factor * age_factor * density_factor
        
        # Ensure within reasonable bounds
        min_radius = 0.3  # Minimum 300m
        max_radius = location_context['max_radius']
        
        final_radius = max(min_radius, min(calculated_radius, max_radius))
        
        print(f"🧮 Radius calculation:")
        print(f"   Base: {base_radius}km")
        print(f"   Feature factor ({max_features} buildings): {feature_factor}x")
        print(f"   Age factor: {age_factor}x")
        print(f"   Density factor: {density_factor}x")
        print(f"   Final radius: {final_radius:.1f}km")
        
        return final_radius
    
    def _search_buildings_at_radius(self, lat: float, lon: float, radius_km: float,
                                   max_features: int, min_year: Optional[int], 
                                   max_year: Optional[int]) -> List[Dict]:
        """Search for buildings at a specific radius."""
        
        try:
            # Convert to RD New for precise bbox calculation
            center_x, center_y = self.transformer_to_rd.transform(lon, lat)
            radius_m = radius_km * 1000
            
            bbox = [
                center_x - radius_m, center_y - radius_m,
                center_x + radius_m, center_y + radius_m
            ]
            
            # Build CQL filter for age requirements
            cql_filters = []
            if min_year:
                cql_filters.append(f"bouwjaar >= {min_year}")
            if max_year:
                cql_filters.append(f"bouwjaar <= {max_year}")
            
            cql_filter = " AND ".join(cql_filters) if cql_filters else None
            
            # Make WFS request
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': 'bag:pand',
                'outputFormat': 'application/json',
                'count': max_features,
                'srsName': 'EPSG:28992',
                'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
            }
            
            if cql_filter:
                params['cql_filter'] = cql_filter
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            raw_features = data.get('features', [])
            processed_buildings = []
            
            for feature in raw_features:
                processed_building = self._process_building_feature(feature)
                if processed_building:
                    processed_buildings.append(processed_building)
            
            return processed_buildings
            
        except Exception as e:
            print(f"❌ Error searching at radius {radius_km}km: {e}")
            return []
    
    def _process_building_feature(self, feature: Dict) -> Optional[Dict]:
        """Process individual building feature from PDOK."""
        try:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            if not geometry:
                return None
            
            # Calculate centroid and convert to WGS84
            centroid_rd = self._calculate_centroid_rd(geometry)
            if not centroid_rd:
                return None
            
            # Convert to WGS84
            centroid_wgs84 = self.transformer_to_wgs84.transform(centroid_rd[0], centroid_rd[1])
            lat, lon = centroid_wgs84[1], centroid_wgs84[0]
            
            # Convert geometry to WGS84
            wgs84_geometry = self._convert_geometry_to_wgs84(geometry)
            
            # Extract building information
            building_id = props.get('identificatie', 'Unknown')
            building_year = props.get('bouwjaar')
            building_status = props.get('status', 'Unknown')
            area_min = props.get('oppervlakte_min', 0)
            area_max = props.get('oppervlakte_max', 0)
            num_units = props.get('aantal_verblijfsobjecten', 0)
            
            # Create building name
            building_name = f"Building {building_id[-6:]}" if len(building_id) > 6 else building_id
            if building_year:
                building_name += f" ({building_year})"
            
            return {
                "name": building_name,
                "lat": float(lat),
                "lon": float(lon),
                "description": "",  # Will be filled later with distance info
                "geometry": wgs84_geometry,
                "properties": {
                    **props,
                    "area_m2": area_max or area_min,
                    "centroid_lat": float(lat),
                    "centroid_lon": float(lon)
                }
            }
            
        except Exception as e:
            print(f"❌ Error processing building feature: {e}")
            return None
    
    def _apply_search_strategy(self, buildings: List[Dict], max_features: int, 
                             strategy: str, target_lat: float, target_lon: float) -> List[Dict]:
        """Apply search strategy to select final buildings."""
        
        if len(buildings) <= max_features:
            selected_buildings = buildings
        else:
            if strategy == "nearest":
                # Always sort by distance first - THIS IS THE KEY FIX!
                buildings.sort(key=lambda x: x.get('distance_km', 999))
                selected_buildings = buildings[:max_features]
                
            elif strategy == "historic_priority":
                # Prioritize older buildings, but still consider distance
                buildings.sort(key=lambda x: (
                    x.get('properties', {}).get('bouwjaar', 3000),  # Older first
                    x.get('distance_km', 999)  # Then closer
                ))
                selected_buildings = buildings[:max_features]
                
            elif strategy == "diverse_sample":
                # Mix of closest and historic buildings
                buildings.sort(key=lambda x: x.get('distance_km', 999))
                closest_half = buildings[:max_features//2]
                
                remaining = buildings[max_features//2:]
                remaining.sort(key=lambda x: x.get('properties', {}).get('bouwjaar', 3000))
                historic_half = remaining[:max_features - len(closest_half)]
                
                selected_buildings = closest_half + historic_half
                
            else:  # random or unknown strategy
                buildings.sort(key=lambda x: x.get('distance_km', 999))
                selected_buildings = buildings[:max_features]
        
        # Add distance descriptions
        for i, building in enumerate(selected_buildings):
            distance = building.get('distance_km', 0)
            year = building.get('properties', {}).get('bouwjaar')
            status = building.get('properties', {}).get('status', 'Unknown')
            area = building.get('properties', {}).get('area_m2', 0)
            units = building.get('properties', {}).get('aantal_verblijfsobjecten', 0)
            
            desc_parts = [f"Distance: {distance:.3f}km"]
            if year:
                age = 2024 - year
                desc_parts.append(f"Built: {year} ({age} years old)")
            if status and status != 'Unknown':
                desc_parts.append(f"Status: {status}")
            if area > 0:
                desc_parts.append(f"Area: {area:.0f}m²")
            if units > 0:
                desc_parts.append(f"Units: {units}")
            
            building['description'] = " | ".join(desc_parts)
        
        return selected_buildings
    
    def _create_intelligent_description(self, buildings: List[Dict], location: str, 
                                      loc_data: Dict, location_context: Dict,
                                      strategy: str, max_features: int,
                                      min_year: Optional[int], max_year: Optional[int]) -> str:
        """Create intelligent description based on context."""
        
        location_name = loc_data.get('name', location)
        distances = [b.get('distance_km', 0) for b in buildings]
        years = [b.get('properties', {}).get('bouwjaar') for b in buildings if b.get('properties', {}).get('bouwjaar')]
        
        text_parts = []
        
        # Context-aware title
        if location_context['type'] == 'specific_address':
            text_parts.append(f"## Buildings near {location_name} (Address-Based Search)")
            text_parts.append(f"\nI found **{len(buildings)} buildings** near the specific address **{location_name}**, starting from the exact location and expanding outward.")
        elif location_context['type'] == 'city':
            text_parts.append(f"## Buildings in {location_name} (City-Wide Search)")
            text_parts.append(f"\nI found **{len(buildings)} buildings** in **{location_name}** using intelligent city-scale search.")
        else:
            text_parts.append(f"## Buildings near {location_name}")
            text_parts.append(f"\nI found **{len(buildings)} buildings** near **{location_name}** using intelligent proximity search.")
        
        # Strategy explanation
        strategy_descriptions = {
            'nearest': 'sorted by distance from your specified location (closest first)',
            'historic_priority': 'prioritizing historic buildings while considering proximity',
            'diverse_sample': 'providing a diverse mix of nearby and historic buildings',
            'random': 'with varied selection across the search area'
        }
        
        strategy_desc = strategy_descriptions.get(strategy, 'using intelligent selection')
        text_parts.append(f"**Selection strategy**: {strategy_desc}")
        
        # Distance and area information
        if distances:
            min_dist = min(distances)
            max_dist = max(distances)
            avg_dist = sum(distances) / len(distances)
            text_parts.append(f"**Distance range**: {min_dist:.3f}km to {max_dist:.3f}km (average: {avg_dist:.3f}km)")
        
        # Age information
        if years:
            min_year_found = min(years)
            max_year_found = max(years)
            avg_year = sum(years) / len(years)
            text_parts.append(f"**Construction period**: {min_year_found} to {max_year_found} (average: {avg_year:.0f})")
        
        # Age filter information
        if max_year:
            age_requirement = 2024 - max_year
            text_parts.append(f"**Age filter**: Buildings older than {age_requirement} years (built before {max_year + 1})")
        
        # Building list (showing progression from closest)
        text_parts.append(f"\n**Buildings found (sorted by proximity)**:")
        for i, building in enumerate(buildings[:8]):  # Show up to 8
            props = building.get('properties', {})
            year = props.get('bouwjaar', 'Unknown year')
            area = props.get('area_m2', 0)
            distance = building.get('distance_km', 0)
            
            desc = f"{i+1}. **{building['name']}** - {distance:.3f}km away"
            if year != 'Unknown year':
                age = 2024 - year if isinstance(year, int) else 'Unknown'
                desc += f", Built {year} ({age} years old)"
            if area > 0:
                desc += f", {area:.0f}m²"
            
            text_parts.append(desc)
        
        if len(buildings) > 8:
            text_parts.append(f"... and {len(buildings) - 8} more buildings")
        
        # Location details
        if loc_data.get('description'):
            text_parts.append(f"\n**Search center**: {loc_data['description']}")
        
        text_parts.append(f"\nAll **{len(buildings)} buildings** are displayed on the map, **starting from your specified location and expanding outward**. Click any building for detailed information.")
        
        return "\n".join(text_parts)
    
    def _calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using Haversine formula."""
        try:
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                math.cos(lat1_rad) * math.cos(lat2_rad) * 
                math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        except:
            return 999.0
    
    def _calculate_centroid_rd(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """Calculate centroid in RD New coordinates."""
        try:
            if geometry['type'] == 'Polygon':
                coords = geometry['coordinates'][0]
                if coords and len(coords) > 0:
                    avg_x = sum(coord[0] for coord in coords) / len(coords)
                    avg_y = sum(coord[1] for coord in coords) / len(coords)
                    return (avg_x, avg_y)
            elif geometry['type'] == 'Point':
                return tuple(geometry['coordinates'])
            return None
        except:
            return None
    
    def _convert_geometry_to_wgs84(self, geometry: Dict) -> Dict:
        """Convert geometry from RD New to WGS84."""
        try:
            if geometry['type'] == 'Polygon':
                wgs84_coords = []
                for ring in geometry['coordinates']:
                    wgs84_ring = []
                    for coord in ring:
                        wgs84_coord = self.transformer_to_wgs84.transform(coord[0], coord[1])
                        wgs84_ring.append([wgs84_coord[0], wgs84_coord[1]])
                    wgs84_coords.append(wgs84_ring)
                return {
                    'type': 'Polygon',
                    'coordinates': wgs84_coords
                }
            elif geometry['type'] == 'Point':
                wgs84_coord = self.transformer_to_wgs84.transform(geometry['coordinates'][0], geometry['coordinates'][1])
                return {
                    'type': 'Point',
                    'coordinates': [wgs84_coord[0], wgs84_coord[1]]
                }
            return geometry
        except:
            return geometry