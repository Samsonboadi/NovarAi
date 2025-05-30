import math
import requests
from datetime import datetime
from smolagents import Tool

class PDOKBuildingsRealTool(Tool):
    """Enhanced PDOK Buildings tool with distance-based building selection around specific locations."""
    
    name = "get_pdok_buildings_with_description"
    description = "Get REAL building data from PDOK WFS service using distance-based selection around a specific location. Buildings are sorted by actual proximity to the specified point."
    inputs = {
        "location": {"type": "string", "description": "Location name (e.g., 'Amsterdam train station', 'Utrecht Centraal', 'Kloosterstraat 27 Ten Boer')"},
        "max_features": {"type": "integer", "description": "Maximum buildings to return (default: 20)", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "radius_km": {"type": "number", "description": "Search radius in kilometers (default: 2.0)", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
        self.typename = "bag:pand"
        self.srs = "EPSG:28992"
        self.version = "2.0.0"
        
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            print("✅ PyProj coordinate transformers initialized")
        except ImportError:
            print("❌ Warning: pyproj not available - coordinate transformation disabled")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def calculate_distance_km(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula."""
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
    
    def forward(self, location, max_features=20, min_year=None, max_year=None, radius_km=2.0):
        """Get REAL buildings from PDOK with DISTANCE-BASED selection around the specified location."""
        global current_map_state
        
        try:
            print(f"\n🏗️ === DISTANCE-BASED PDOK BUILDINGS SEARCH ===")
            print(f"Location: {location}")
            print(f"Max features: {max_features}")
            print(f"Search radius: {radius_km}km")
            print(f"🎯 Using DISTANCE-BASED selection to find closest buildings")
            
            # Step 1: Enhanced location search using PDOK Locatieserver
            print("🔍 Finding exact coordinates for location...")
            from tools.pdok_location import find_location_coordinates
            loc_data = find_location_coordinates(location)
            
            if "error" in loc_data:
                return {
                    "text_description": f"❌ Could not find location: {location}. {loc_data['error']}",
                    "geojson_data": [],
                    "error": loc_data["error"]
                }
            
            target_lat, target_lon = loc_data["lat"], loc_data["lon"]
            print(f"✅ Target location coordinates: {target_lat:.6f}, {target_lon:.6f}")
            print(f"✅ Location details: {loc_data.get('description', 'N/A')}")
            
            # Validate coordinates are in Netherlands
            from tools.pdok_location import pdok_service
            if not pdok_service.is_in_netherlands(target_lat, target_lon):
                return {
                    "text_description": f"❌ Location '{location}' appears to be outside the Netherlands (lat: {target_lat:.6f}, lon: {target_lon:.6f}). Please specify a Dutch location.",
                    "geojson_data": [],
                    "error": "Location outside Netherlands"
                }
            
            # Step 2: Convert to RD New coordinates and create LARGER search area
            if self.transformer_to_rd:
                center_x, center_y = self.transformer_to_rd.transform(target_lon, target_lat)
                
                # IMPORTANT: Use larger initial search radius to get more candidates
                # We'll filter by distance later, so we need a bigger net
                search_radius_m = radius_km * 2000  # Double the search radius for initial query
                bbox = [center_x - search_radius_m, center_y - search_radius_m, 
                       center_x + search_radius_m, center_y + search_radius_m]
                use_rd_coordinates = True
                print(f"✅ Converted to RD New: {center_x:.2f}, {center_y:.2f}")
                print(f"📏 Initial search radius: {search_radius_m/1000:.1f}km (will filter to {radius_km}km by distance)")
            else:
                # Fallback to WGS84 bounding box
                buffer = radius_km * 0.02  # Larger buffer for initial search
                bbox = [target_lon - buffer, target_lat - buffer, target_lon + buffer, target_lat + buffer]
                use_rd_coordinates = False
                print("⚠️ Using WGS84 coordinates (less accurate)")
            
            # Step 3: Build CQL filters
            cql_filters = []
            if min_year:
                cql_filters.append(f"bouwjaar >= {min_year}")
            if max_year:
                cql_filters.append(f"bouwjaar <= {max_year}")
            cql_filter = " AND ".join(cql_filters) if cql_filters else None
            
            # Step 4: Build PDOK WFS request with LARGER count to get more candidates
            params = {
                'service': 'WFS',
                'version': self.version,
                'request': 'GetFeature',
                'typeName': self.typename,
                'outputFormat': 'application/json',
                'count': max_features * 5,  # Get 5x more features initially for distance filtering
                'srsName': self.srs if use_rd_coordinates else 'EPSG:4326',
                'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{self.srs if use_rd_coordinates else 'EPSG:4326'}"
            }
            if cql_filter:
                params['cql_filter'] = cql_filter
            
            print(f"🌐 Making PDOK WFS request for building candidates...")
            print(f"📦 Requesting {params['count']} candidate buildings for distance filtering")
            
            # Step 5: Make the request to PDOK
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_features = data.get('features', [])
            
            print(f"📦 PDOK returned {len(raw_features)} candidate buildings")
            
            if not raw_features:
                return {
                    "text_description": f"❌ No buildings found around {location} from PDOK service. The location was found (coordinates {target_lat:.6f}, {target_lon:.6f}), but no buildings were found in a {radius_km}km radius. Try increasing the search radius.",
                    "geojson_data": [],
                    "error": "No buildings found in PDOK data"
                }
            
            # Step 6: Process features and calculate distances
            print(f"📏 Calculating distances to target location...")
            building_candidates = []
            
            for i, feature in enumerate(raw_features):
                try:
                    props = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    if not geometry:
                        continue
                    
                    # Calculate building centroid
                    building_lat, building_lon = self._calculate_building_centroid(geometry, use_rd_coordinates)
                    
                    if building_lat == 0 or building_lon == 0:
                        continue
                    
                    # Calculate distance to target location
                    distance_km = self.calculate_distance_km(target_lat, target_lon, building_lat, building_lon)
                    
                    # Only include buildings within the specified radius
                    if distance_km <= radius_km:
                        building_candidates.append({
                            'feature': feature,
                            'distance_km': distance_km,
                            'building_lat': building_lat,
                            'building_lon': building_lon,
                            'props': props,
                            'geometry': geometry
                        })
                        
                        if i < 5:  # Debug first few buildings
                            building_id = props.get('identificatie', f'Building_{i+1}')[-6:]
                            print(f"   Building {building_id}: {distance_km:.3f}km away")
                
                except Exception as e:
                    continue
            
            print(f"🎯 Found {len(building_candidates)} buildings within {radius_km}km of target location")
            
            if not building_candidates:
                return {
                    "text_description": f"❌ No buildings found within {radius_km}km of {location}. Found {len(raw_features)} buildings in the wider area, but none were close enough to the target location. Try increasing the search radius.",
                    "geojson_data": [],
                    "error": f"No buildings within {radius_km}km radius"
                }
            
            # Step 7: Sort by distance (closest first) and take requested number
            building_candidates.sort(key=lambda x: x['distance_km'])
            selected_buildings = building_candidates[:max_features]
            
            print(f"📍 Selected {len(selected_buildings)} closest buildings:")
            for i, building in enumerate(selected_buildings[:5]):
                building_id = building['props'].get('identificatie', f'Building_{i+1}')[-6:]
                print(f"   {i+1}. Building {building_id}: {building['distance_km']:.3f}km")
            
            # Step 8: Process selected buildings into final format
            processed_features = []
            
            for i, building_data in enumerate(selected_buildings):
                try:
                    feature = building_data['feature']
                    props = building_data['props']
                    geometry = building_data['geometry']
                    distance_km = building_data['distance_km']
                    building_lat = building_data['building_lat']
                    building_lon = building_data['building_lon']
                    
                    # Validate and fix geometry
                    validated_geometry = self._validate_and_fix_geometry(geometry, use_rd_coordinates)
                    if not validated_geometry:
                        continue
                    
                    # Extract building information
                    building_id = props.get('identificatie', f'Building_{i+1}')
                    building_year = props.get('bouwjaar', 'Unknown')
                    building_status = props.get('status', 'Unknown')
                    
                    # Calculate area
                    area_m2 = self._calculate_area(validated_geometry)
                    
                    # Create building name with distance
                    building_name = f"Building {building_id[-6:]}" if len(building_id) > 6 else building_id
                    if building_year and building_year != 'Unknown':
                        building_name += f" ({building_year})"
                    
                    # Create description with distance
                    desc_parts = [f"Distance: {distance_km:.3f}km"]  # Distance first!
                    if building_year and building_year != 'Unknown':
                        desc_parts.append(f"Built: {building_year}")
                    if building_status and building_status != 'Unknown':
                        desc_parts.append(f"Status: {building_status}")
                    if area_m2 > 0:
                        desc_parts.append(f"Area: {area_m2:.0f}m²")
                    
                    num_units = props.get('aantal_verblijfsobjecten')
                    if num_units:
                        desc_parts.append(f"Units: {num_units}")
                    
                    description = " | ".join(desc_parts)
                    
                    # Create enhanced feature
                    enhanced_feature = {
                        "name": building_name,
                        "lat": float(building_lat),
                        "lon": float(building_lon),
                        "description": description,
                        "geometry": validated_geometry,
                        "properties": {
                            **props,
                            "area_m2": area_m2,
                            "centroid_lat": float(building_lat),
                            "centroid_lon": float(building_lon),
                            "distance_km": distance_km,  # Add distance to properties
                            "target_location": location
                        }
                    }
                    
                    processed_features.append(enhanced_feature)
                    
                except Exception as feature_error:
                    print(f"❌ Error processing building {i+1}: {feature_error}")
                    continue
            
            if not processed_features:
                return {
                    "text_description": f"❌ No valid buildings could be processed around {location}.",
                    "geojson_data": [],
                    "error": "No valid buildings processed"
                }
            
            print(f"🎉 Successfully processed {len(processed_features)} buildings by distance from {location}")
            
            # Step 9: Create detailed text description
            location_name = loc_data.get('name', location)
            total_area = sum(f['properties'].get('area_m2', 0) for f in processed_features)
            years = [f['properties'].get('bouwjaar') for f in processed_features if f['properties'].get('bouwjaar')]
            
            # Distance statistics
            distances = [f['properties']['distance_km'] for f in processed_features]
            closest_distance = min(distances)
            farthest_distance = max(distances)
            avg_distance = sum(distances) / len(distances)
            
            text_parts = [f"## Real Buildings near {location_name} (Distance-Based Selection)"]
            text_parts.append(f"\nI found **{len(processed_features)} real buildings** near {location_name}, selected by actual proximity to your specified location.")
            
            # Distance information
            text_parts.append(f"\n**Distance range**: {closest_distance:.3f}km to {farthest_distance:.3f}km (average: {avg_distance:.3f}km)")
            text_parts.append(f"**Target location**: {target_lat:.6f}°N, {target_lon:.6f}°E")
            
            if total_area > 0:
                text_parts.append(f"\n**Total building area**: {total_area:,.0f}m²")
            
            if years:
                avg_year = sum(years) / len(years)
                min_year_found = min(years)
                max_year_found = max(years)
                text_parts.append(f"\n**Construction period**: {min_year_found} to {max_year_found} (average: {avg_year:.0f})")
            
            # Add closest buildings list
            text_parts.append(f"\n**Closest buildings to {location_name}**:")
            for i, building in enumerate(processed_features[:5]):
                props = building['properties']
                year = props.get('bouwjaar', 'Unknown year')
                area = props.get('area_m2', 0)
                distance = props.get('distance_km', 0)
                text_parts.append(f"* **{building['name']}** - {distance:.3f}km away, Built {year}, {area:.0f}m²")
            
            # Add location details from enhanced search
            if loc_data.get('pdok_data'):
                pdok_info = loc_data['pdok_data']
                if pdok_info.get('gemeente'):
                    text_parts.append(f"\n**Municipality**: {pdok_info['gemeente']}")
                if pdok_info.get('provincie'):
                    text_parts.append(f"**Province**: {pdok_info['provincie']}")
            
            text_parts.append(f"\nAll **{len(processed_features)} buildings** are displayed on the map, sorted by distance from your specified location '{location}'. Each building shows its exact distance in the popup.")
            
            text_description = "\n".join(text_parts)
            
            # Step 10: Update map state
            global current_map_state
            current_map_state["features"] = processed_features
            current_map_state["last_updated"] = datetime.now().isoformat()
            current_map_state["center"] = [target_lon, target_lat]
            current_map_state["zoom"] = 15  # Closer zoom for detailed view
            
            print(f"✅ Updated map state with {len(processed_features)} distance-sorted buildings")
            
            return {
                "text_description": text_description,
                "geojson_data": processed_features
            }
            
        except Exception as e:
            error_msg = f"Distance-based PDOK tool error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error retrieving buildings around {location}: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _calculate_building_centroid(self, geometry, use_rd_coordinates):
        """Calculate the centroid of a building geometry."""
        try:
            if geometry['type'] == 'Polygon':
                coords = geometry['coordinates'][0]
                if coords and len(coords) > 0:
                    avg_x = sum(coord[0] for coord in coords) / len(coords)
                    avg_y = sum(coord[1] for coord in coords) / len(coords)
                    
                    # Convert to WGS84 if needed
                    if self.transformer_to_wgs84 and use_rd_coordinates:
                        wgs84_coords = self.transformer_to_wgs84.transform(avg_x, avg_y)
                        return wgs84_coords[1], wgs84_coords[0]  # lat, lon
                    else:
                        return avg_y, avg_x  # lat, lon
                        
            elif geometry['type'] == 'Point':
                coords = geometry['coordinates']
                if self.transformer_to_wgs84 and use_rd_coordinates:
                    wgs84_coords = self.transformer_to_wgs84.transform(coords[0], coords[1])
                    return wgs84_coords[1], wgs84_coords[0]  # lat, lon
                else:
                    return coords[1], coords[0]  # lat, lon
                    
        except Exception as e:
            print(f"Error calculating centroid: {e}")
            
        return 0, 0
    
    def _validate_and_fix_geometry(self, geometry, use_rd_coordinates):
        """Validate and fix geometry data structure, converting to WGS84 if needed."""
        try:
            if not isinstance(geometry, dict):
                return None
                
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates')
            
            if not geom_type or not coordinates:
                return None
            
            # Convert coordinates to WGS84 if they're in RD New
            if self.transformer_to_wgs84 and use_rd_coordinates:
                if geom_type == 'Polygon':
                    wgs84_coords = []
                    for ring in coordinates:
                        wgs84_ring = []
                        for coord in ring:
                            wgs84_coord = self.transformer_to_wgs84.transform(coord[0], coord[1])
                            wgs84_ring.append([wgs84_coord[0], wgs84_coord[1]])
                        wgs84_coords.append(wgs84_ring)
                    coordinates = wgs84_coords
                elif geom_type == 'Point':
                    wgs84_coord = self.transformer_to_wgs84.transform(coordinates[0], coordinates[1])
                    coordinates = [wgs84_coord[0], wgs84_coord[1]]
            
            return {
                'type': geom_type,
                'coordinates': coordinates
            }
            
        except Exception as e:
            print(f"Error validating geometry: {e}")
            return None
    
    def _calculate_area(self, geometry):
        """Calculate approximate area of polygon."""
        try:
            if geometry['type'] != 'Polygon':
                return 50  # Default area for non-polygons
            
            coords = geometry['coordinates'][0]
            if not coords or len(coords) < 3:
                return 50
            
            # Simple area calculation for display purposes
            # Note: This is approximate for WGS84 coordinates
            n = len(coords)
            area = 0.5 * abs(sum(coords[i][0] * coords[(i + 1) % n][1] - 
                               coords[(i + 1) % n][0] * coords[i][1] 
                               for i in range(n)))
            
            # Convert to square meters (very rough approximation)
            return area * 111000 * 111000  # Rough conversion factor
            
        except Exception:
            return 50