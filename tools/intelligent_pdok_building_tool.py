import math
import requests
import re
from datetime import datetime
from smolagents import Tool
from typing import Dict, List, Optional, Tuple

class IntelligentPDOKBuildingTool(Tool):
    """
    FIXED: Intelligent PDOK Buildings tool with TRUE address-centered search.
    
    Key Fixes:
    - Uses exact address coordinates as center point
    - Sorts by actual distance from address (not random)
    - Progressive radius expansion from address
    - Area filtering AFTER distance sorting
    - Proper proximity-based selection
    """
    
    name = "get_buildings_intelligent"
    description = "Get buildings with FIXED address-centered search and proper distance-based selection"
    inputs = {
        "location": {"type": "string", "description": "Location (e.g., 'Leonard Springerlaan 37, Groningen')"},
        "max_features": {"type": "integer", "description": "Number of buildings wanted", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "min_area_m2": {"type": "number", "description": "Minimum area in square meters", "nullable": True},
        "search_strategy": {"type": "string", "description": "Search strategy: 'address_centered' (default), 'nearest'", "nullable": True}
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
            print("✅ FIXED Intelligent PDOK tool initialized")
        except ImportError:
            print("❌ PyProj required for intelligent PDOK tool")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, location, max_features=10, min_year=None, max_year=None, min_area_m2=None, search_strategy="address_centered"):
        """FIXED: Address-centered building search with proper proximity sorting."""
        
        try:
            print(f"\n🎯 === FIXED ADDRESS-CENTERED SEARCH ===")
            print(f"Location: {location}")
            print(f"Requested buildings: {max_features}")
            print(f"Min area: {min_area_m2}m²" if min_area_m2 else "No area filter")
            print(f"🔧 USING FIXED ADDRESS-CENTERED LOGIC")
            
            # Step 1: Enhanced location analysis with better address detection
            location_context = self._analyze_location_context_fixed(location)
            print(f"📍 Location type: {location_context['type']}")
            print(f"🎯 Search strategy: {location_context['strategy']}")
            
            # Step 2: Get EXACT coordinates of the address
            from tools.pdok_location import find_location_coordinates
            loc_data = find_location_coordinates(location)
            
            if "error" in loc_data:
                return {
                    "text_description": f"❌ Could not find exact address: {location}. {loc_data['error']}",
                    "geojson_data": [],
                    "error": loc_data["error"]
                }
            
            target_lat, target_lon = loc_data["lat"], loc_data["lon"]
            print(f"✅ EXACT address coordinates: {target_lat:.6f}, {target_lon:.6f}")
            print(f"📍 Address details: {loc_data.get('description', 'N/A')}")
            
            # Step 3: FIXED - Use small initial radius for addresses
            if location_context['type'] == 'specific_address':
                initial_radius = 0.2  # Start with 200m for addresses
                max_radius = 2.0      # Max 2km for addresses  
                print(f"🏠 Specific address detected - starting with {initial_radius}km radius")
            else:
                initial_radius = location_context.get('initial_radius', 1.0)
                max_radius = location_context.get('max_radius', 10.0)
            
            # Step 4: FIXED - Progressive search with ADDRESS AS CENTER
            all_buildings = []
            current_radius = initial_radius
            attempts = 0
            
            print(f"🎯 Starting progressive search from EXACT ADDRESS coordinates")
            
            while len(all_buildings) < max_features * 2 and current_radius <= max_radius and attempts < 5:
                attempts += 1
                print(f"\n🔍 Search attempt {attempts}: radius {current_radius:.1f}km from address")
                
                # Get buildings at current radius FROM THE ADDRESS
                buildings = self._search_buildings_from_address(
                    target_lat, target_lon, current_radius,
                    max_features * 5,  # Get more candidates
                    min_year, max_year
                )
                
                if buildings:
                    print(f"📦 Found {len(buildings)} buildings in {current_radius:.1f}km radius")
                    
                    # CRITICAL FIX: Calculate distance from ADDRESS for each building
                    buildings_with_distance = []
                    for building in buildings:
                        building_lat = building.get('lat', 0)
                        building_lon = building.get('lon', 0)
                        
                        if building_lat != 0 and building_lon != 0:
                            distance = self._calculate_distance_km(
                                target_lat, target_lon,    # FROM ADDRESS
                                building_lat, building_lon  # TO BUILDING
                            )
                            building['distance_from_address'] = distance
                            building['distance_km'] = distance  # For compatibility
                            buildings_with_distance.append(building)
                    
                    # CRITICAL FIX: Sort by distance FROM ADDRESS (not random!)
                    buildings_with_distance.sort(key=lambda x: x['distance_from_address'])
                    
                    print(f"🎯 Buildings sorted by distance from address:")
                    for i, building in enumerate(buildings_with_distance[:5]):
                        dist = building['distance_from_address']
                        props = building.get('properties', {})
                        year = props.get('bouwjaar', 'Unknown')
                        area = props.get('area_m2', 0)
                        print(f"   {i+1}. {dist:.3f}km - Year: {year}, Area: {area:.0f}m²")
                    
                    # Add unique buildings (avoid duplicates)
                    for building in buildings_with_distance:
                        building_id = building.get('properties', {}).get('identificatie')
                        if building_id and not any(b.get('properties', {}).get('identificatie') == building_id for b in all_buildings):
                            all_buildings.append(building)
                
                if len(all_buildings) >= max_features * 2:
                    print(f"✅ Found enough candidates ({len(all_buildings)}) within {current_radius:.1f}km")
                    break
                
                # Expand radius for next attempt
                current_radius *= 1.5  # Smaller expansion for addresses
                print(f"🔄 Expanding search radius to {current_radius:.1f}km")
            
            if not all_buildings:
                return {
                    "text_description": f"❌ No buildings found near {location} within {current_radius:.1f}km radius.",
                    "geojson_data": [],
                    "error": "No buildings found"
                }
            
            # Step 5: FIXED - Apply area filter to DISTANCE-SORTED buildings
            filtered_buildings = []
            if min_area_m2:
                print(f"\n🔽 Applying area filter: buildings > {min_area_m2}m²")
                for building in all_buildings:
                    props = building.get('properties', {})
                    
                    # Get area from multiple possible fields
                    area = None
                    for area_field in ['area_m2', 'oppervlakte_max', 'oppervlakte_min']:
                        area_value = props.get(area_field)
                        if area_value and isinstance(area_value, (int, float)) and area_value > 0:
                            area = float(area_value)
                            break
                    
                    if area and area >= min_area_m2:
                        # Update area in properties for consistency
                        building['properties']['area_m2'] = area
                        filtered_buildings.append(building)
                        
                        if len(filtered_buildings) <= 5:
                            dist = building.get('distance_from_address', 0)
                            print(f"   ✅ Building {len(filtered_buildings)}: {area:.0f}m² at {dist:.3f}km")
                
                if not filtered_buildings:
                    return {
                        "text_description": f"❌ No buildings near {location} with area ≥ {min_area_m2}m². Found {len(all_buildings)} buildings but none meet area requirement.",
                        "geojson_data": [],
                        "error": f"No buildings with area ≥ {min_area_m2}m²"
                    }
                
                print(f"📊 {len(filtered_buildings)} buildings meet area criteria (≥ {min_area_m2}m²)")
            else:
                filtered_buildings = all_buildings
                print(f"📊 No area filter - using all {len(filtered_buildings)} buildings")
            
            # Step 6: Take the closest buildings that meet criteria
            final_buildings = filtered_buildings[:max_features]
            
            print(f"\n🎉 Final selection: {len(final_buildings)} closest buildings")
            for i, building in enumerate(final_buildings):
                dist = building.get('distance_from_address', 0)
                props = building.get('properties', {})
                area = props.get('area_m2', 0)
                year = props.get('bouwjaar', 'Unknown')
                print(f"   {i+1}. {dist:.3f}km - {area:.0f}m² - Built {year}")
            
            # Step 7: Create enhanced response
            text_description = self._create_address_centered_description(
                final_buildings, location, loc_data, min_area_m2, max_features
            )
            
            return {
                "text_description": text_description,
                "geojson_data": final_buildings
            }
            
        except Exception as e:
            error_msg = f"FIXED Intelligent PDOK tool error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error retrieving buildings near {location}: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _analyze_location_context_fixed(self, location: str) -> Dict:
        """FIXED: Better address pattern detection."""
        location_lower = location.lower()
        
        # Enhanced address patterns for Dutch addresses
        address_patterns = [
            r'\w+straat\s+\d+',         # "springerlaan 37"
            r'\d+\s+\w+straat',         # "37 springerlaan"  
            r'\w+weg\s+\d+',            # "hoofdweg 123"
            r'\w+laan\s+\d+',           # "parklaan 45" 
            r'\w+plein\s+\d+',          # "marktplein 12"
            r'\w+gracht\s+\d+',         # "keizersgracht 123"
            r'\w+kade\s+\d+',           # "noorderkade 45"
            r'\d+[a-z]?\s+\w+',         # "37a springerlaan"
        ]
        
        is_specific_address = any(re.search(pattern, location_lower) for pattern in address_patterns)
        
        if is_specific_address:
            print("🏠 DETECTED: Specific street address")
            return {
                'type': 'specific_address',
                'strategy': 'address_centered',
                'initial_radius': 0.2,  # 200m for addresses
                'expansion_factor': 1.5,
                'max_radius': 2.0,      # Max 2km for addresses
                'density_estimate': 'high',
                'description': 'specific street address'
            }
        else:
            print("🏙️ DETECTED: General location (city/area)")
            return {
                'type': 'general_location',
                'strategy': 'nearest',
                'initial_radius': 1.0,  # 1km for general locations
                'expansion_factor': 2.0,
                'max_radius': 10.0,
                'density_estimate': 'medium',
                'description': 'general location'
            }
    
    def _search_buildings_from_address(self, address_lat: float, address_lon: float, 
                                     radius_km: float, max_features: int,
                                     min_year: Optional[int], max_year: Optional[int]) -> List[Dict]:
        """FIXED: Search buildings in radius FROM the specific address coordinates."""
        
        try:
            # Convert address coordinates to RD New for precise bbox
            center_x, center_y = self.transformer_to_rd.transform(address_lon, address_lat)
            radius_m = radius_km * 1000
            
            # Create bbox centered on the ADDRESS
            bbox = [
                center_x - radius_m, center_y - radius_m,
                center_x + radius_m, center_y + radius_m
            ]
            
            print(f"🎯 Searching {radius_km:.1f}km radius from address ({address_lat:.6f}, {address_lon:.6f})")
            print(f"📦 RD New bbox: {bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}")
            
            # Build age filters if specified
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
                print(f"🗓️ Age filter: {cql_filter}")
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            raw_features = data.get('features', [])
            processed_buildings = []
            
            print(f"📦 PDOK returned {len(raw_features)} raw features")
            
            for feature in raw_features:
                processed_building = self._process_building_feature_fixed(feature)
                if processed_building:
                    processed_buildings.append(processed_building)
            
            print(f"✅ Processed {len(processed_buildings)} valid buildings")
            return processed_buildings
            
        except Exception as e:
            print(f"❌ Error searching buildings from address: {e}")
            return []
    
    def _process_building_feature_fixed(self, feature: Dict) -> Optional[Dict]:
        """FIXED: Process building with proper area calculation."""
        try:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            if not geometry:
                return None
            
            # Calculate centroid in RD New, then convert to WGS84
            centroid_rd = self._calculate_centroid_rd(geometry)
            if not centroid_rd:
                return None
            
            # Convert to WGS84
            centroid_wgs84 = self.transformer_to_wgs84.transform(centroid_rd[0], centroid_rd[1])
            lat, lon = centroid_wgs84[1], centroid_wgs84[0]
            
            # Convert geometry to WGS84
            wgs84_geometry = self._convert_geometry_to_wgs84(geometry)
            
            # Extract building information with better area handling
            building_id = props.get('identificatie', 'Unknown')
            building_year = props.get('bouwjaar')
            building_status = props.get('status', 'Unknown')
            
            # FIXED: Better area calculation from multiple sources
            area_m2 = 0
            for area_field in ['oppervlakte_max', 'oppervlakte_min']:
                area_value = props.get(area_field)
                if area_value and isinstance(area_value, (int, float)) and area_value > 0:
                    area_m2 = float(area_value)
                    break
            
            # Create building name
            building_name = f"Building {building_id[-6:]}" if len(building_id) > 6 else building_id
            if building_year:
                building_name += f" ({building_year})"
            
            return {
                "name": building_name,
                "lat": float(lat),
                "lon": float(lon),
                "description": "",  # Will be filled later
                "geometry": wgs84_geometry,
                "properties": {
                    **props,
                    "area_m2": area_m2,
                    "centroid_lat": float(lat),
                    "centroid_lon": float(lon)
                }
            }
            
        except Exception as e:
            print(f"❌ Error processing building: {e}")
            return None
    
    def _create_address_centered_description(self, buildings: List[Dict], location: str, 
                                           loc_data: Dict, min_area_m2: Optional[float], 
                                           max_features: int) -> str:
        """Create description emphasizing address-centered search."""
        
        location_name = loc_data.get('name', location)
        distances = [b.get('distance_from_address', 0) for b in buildings]
        areas = [b.get('properties', {}).get('area_m2', 0) for b in buildings if b.get('properties', {}).get('area_m2', 0) > 0]
        years = [b.get('properties', {}).get('bouwjaar') for b in buildings if b.get('properties', {}).get('bouwjaar')]
        
        text_parts = []
        
        # Address-focused title
        text_parts.append(f"## Buildings near {location_name} (Address-Centered Search)")
        
        if min_area_m2:
            text_parts.append(f"\nI found **{len(buildings)} buildings** near the specific address **{location_name}** with area ≥ {min_area_m2}m², sorted by distance from the exact address location.")
        else:
            text_parts.append(f"\nI found **{len(buildings)} buildings** near the specific address **{location_name}**, sorted by distance from the exact address location.")
        
        # Address details
        if loc_data.get('description'):
            text_parts.append(f"**Search center**: {loc_data['description']}")
        
        # Distance information - key for address searches
        if distances:
            min_dist = min(distances)
            max_dist = max(distances)
            avg_dist = sum(distances) / len(distances)
            text_parts.append(f"**Distance from address**: {min_dist:.3f}km to {max_dist:.3f}km (average: {avg_dist:.3f}km)")
        
        # Area information if filtered
        if min_area_m2 and areas:
            avg_area = sum(areas) / len(areas)
            max_area = max(areas)
            text_parts.append(f"**Area statistics**: {min_area_m2:.0f}m² to {max_area:.0f}m² (average: {avg_area:.0f}m²)")
        
        # Age information
        if years:
            min_year = min(years)
            max_year = max(years)
            avg_year = sum(years) / len(years)
            text_parts.append(f"**Construction period**: {min_year} to {max_year} (average: {avg_year:.0f})")
        
        # Building list (closest first - this is key!)
        text_parts.append(f"\n**Closest buildings to {location_name} (distance order)**:")
        for i, building in enumerate(buildings[:8]):
            props = building.get('properties', {})
            year = props.get('bouwjaar', 'Unknown')
            area = props.get('area_m2', 0)
            distance = building.get('distance_from_address', 0)
            
            desc = f"{i+1}. **{building['name']}** - {distance:.3f}km from address"
            if area > 0:
                desc += f", {area:.0f}m²"
            if year != 'Unknown':
                desc += f", Built {year}"
            
            text_parts.append(desc)
        
        if len(buildings) > 8:
            text_parts.append(f"... and {len(buildings) - 8} more buildings")
        
        text_parts.append(f"\n**FIXED SEARCH LOGIC**: All buildings are selected based on proximity to the exact address '{location}' and sorted by distance. No random selection!")
        text_parts.append(f"\nAll **{len(buildings)} buildings** are displayed on the map, starting from your address and expanding outward. Click any building for details.")
        
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