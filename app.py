# app.py - Clean PDOK Web Map Chat Assistant
import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool, Tool,DuckDuckGoSearchTool


app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

# Initialize OpenAI model
try:
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_base="https://api.openai.com/v1",
        api_key=os.getenv('OPENAI_API_KEY'),
        max_completion_tokens=8096,
    )
except Exception as e:
    print(f"Error initializing OpenAIServerModel: {e}")
    raise

# Basic location search tool
@tool
def find_location_coordinates(query: str) -> dict:
    """
    Searches for a location and returns its coordinates using Nominatim.
    
    Args:
        query (str): The name of the location to search for (e.g., 'Groningen').
    
    Returns:
        dict: Location data with name, lat, lon, and description.
    """
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "PDOK-WebMap-Chat/1.0"}
        )
        results = response.json()
        if results:
            return {
                "name": query,
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
                "description": results[0].get("display_name", "")
            }
        return {"error": f"No coordinates found for {query}"}
    except Exception as e:
        return {"error": f"Error finding coordinates: {str(e)}"}

# Advanced PDOK Buildings Tool
class PDOKBuildingsAdvancedTool(Tool):
    """Advanced PDOK Buildings tool with full geometry and coordinate transformations"""
    
    name = "get_pdok_buildings"
    description = "Get detailed building data from PDOK WFS service with full polygon geometry, area calculations, and coordinate transformations."
    inputs = {
        "location": {
            "type": "string",
            "description": "Location name (e.g., 'Amsterdam', 'Groningen center')",
            "nullable": True
        },
        "bbox": {
            "type": "array", 
            "description": "Bounding box as [min_x, min_y, max_x, max_y] in RD New coordinates (EPSG:28992)",
            "nullable": True
        },
        "max_features": {
            "type": "integer",
            "description": "Maximum number of buildings to return (default: 10)",
            "nullable": True
        },
        "min_year": {
            "type": "integer",
            "description": "Minimum construction year filter (e.g., 1900)",
            "nullable": True
        },
        "max_year": {
            "type": "integer", 
            "description": "Maximum construction year filter (e.g., 2020)",
            "nullable": True
        },
        "min_area": {
            "type": "integer",
            "description": "Minimum building area in m² (e.g., 100)",
            "nullable": True
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius in kilometers around location (default: 1.0)",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
        self.typename = "bag:pand"
        self.srs = "EPSG:28992"
        self.version = "2.0.0"
        
        # Initialize coordinate transformers
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
        except ImportError:
            print("Warning: pyproj not available - coordinate transformations will be limited")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, location=None, bbox=None, max_features=10, min_year=None, max_year=None, min_area=None, radius_km=1.0):
        """Get buildings from PDOK with advanced filtering and geometry processing."""
        try:
            print(f"\n=== PDOK TOOL DEBUG ===")
            print(f"Input parameters:")
            print(f"  location: {location}")
            print(f"  bbox: {bbox}")
            print(f"  max_features: {max_features}")
            print(f"  min_year: {min_year}")
            print(f"  max_year: {max_year}")
            print(f"  min_area: {min_area}")
            print(f"  radius_km: {radius_km}")
            
            # Handle location-based queries
            if location and not bbox:
                print(f"Getting coordinates for location: {location}")
                loc_data = find_location_coordinates(location)
                if "error" in loc_data:
                    return [{"error": loc_data["error"]}]
                
                lat, lon = loc_data["lat"], loc_data["lon"]
                print(f"Location coordinates: lat={lat}, lon={lon}")
                
                # Convert WGS84 to RD New coordinates if transformer available
                if self.transformer_to_rd:
                    center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                    print(f"Converted to RD New: x={center_x}, y={center_y}")
                    
                    radius_m = radius_km * 1000
                    bbox = [
                        center_x - radius_m,
                        center_y - radius_m,
                        center_x + radius_m,
                        center_y + radius_m
                    ]
                    print(f"Created RD New bbox: {bbox}")
                    use_rd_coordinates = True
                else:
                    print("No pyproj transformer - using WGS84 coordinates")
                    # Fallback: use WGS84 coordinates directly with smaller buffer
                    buffer = radius_km * 0.01  # Approximate degree conversion
                    bbox = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]
                    print(f"Created WGS84 bbox: {bbox}")
                    use_rd_coordinates = False
            else:
                # Assume bbox is already in correct coordinate system
                use_rd_coordinates = True if self.transformer_to_rd else False
                print(f"Using provided bbox: {bbox}")
                print(f"Assuming coordinate system: {'RD New' if use_rd_coordinates else 'WGS84'}")
            
            if not bbox:
                return [{"error": "Must provide either location or bbox parameter"}]
            
            # Build CQL filter for advanced filtering
            cql_filters = []
            if min_year:
                cql_filters.append(f"bouwjaar >= {min_year}")
            if max_year:
                cql_filters.append(f"bouwjaar <= {max_year}")
            
            cql_filter = " AND ".join(cql_filters) if cql_filters else None
            print(f"CQL filter: {cql_filter}")
            
            # Prepare WFS request parameters
            if use_rd_coordinates:
                params = {
                    'service': 'WFS',
                    'version': self.version,
                    'request': 'GetFeature',
                    'typeName': self.typename,
                    'srsName': self.srs,
                    'outputFormat': 'application/json',
                    'count': max_features,
                    'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{self.srs}"
                }
                print(f"Using RD New coordinate system")
            else:
                params = {
                    'service': 'WFS',
                    'version': self.version,
                    'request': 'GetFeature',
                    'typeName': self.typename,
                    'srsName': 'EPSG:4326',
                    'outputFormat': 'application/json',
                    'count': max_features,
                    'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:4326"
                }
                print(f"Using WGS84 coordinate system")
            
            if cql_filter:
                params['cql_filter'] = cql_filter
            
            print(f"PDOK WFS request URL: {self.base_url}")
            print(f"Full parameters: {params}")
            
            # Make request to PDOK
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # Parse JSON response
            try:
                data = response.json()
                print(f"JSON parsing successful")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw response (first 1000 chars): {response.text[:1000]}")
                return [{"error": "Invalid JSON response from PDOK service"}]
            
            raw_features = data.get('features', [])
            print(f"Received {len(raw_features)} raw features from PDOK")
            
            if len(raw_features) > 0:
                print(f"Sample raw feature structure:")
                sample_feature = raw_features[0]
                print(f"  Properties keys: {list(sample_feature.get('properties', {}).keys())}")
                print(f"  Geometry type: {sample_feature.get('geometry', {}).get('type', 'No geometry')}")
                print(f"  Sample properties: {dict(list(sample_feature.get('properties', {}).items())[:3])}")
            
            if not raw_features:
                print("No features found with filters - trying without filters...")
                
                # Try again without CQL filters
                params_no_filter = params.copy()
                if 'cql_filter' in params_no_filter:
                    del params_no_filter['cql_filter']
                
                print(f"Retry without filters: {params_no_filter}")
                
                response2 = requests.get(self.base_url, params=params_no_filter, timeout=30)
                response2.raise_for_status()
                
                try:
                    data2 = response2.json()
                    raw_features = data2.get('features', [])
                    print(f"Received {len(raw_features)} features without filters")
                    
                    if len(raw_features) > 0:
                        print(f"Sample feature without filters:")
                        sample_feature = raw_features[0]
                        print(f"  Properties: {list(sample_feature.get('properties', {}).keys())}")
                        print(f"  Geometry type: {sample_feature.get('geometry', {}).get('type')}")
                except json.JSONDecodeError:
                    print("Failed to parse response without filters")
                
                if not raw_features:
                    print("Still no features - trying direct PDOK test...")
                    
                    # Try with known working Amsterdam coordinates as a test
                    amsterdam_bbox = [120000, 486000, 122000, 488000]  # Known working RD New coordinates
                    params_test = {
                        'service': 'WFS',
                        'version': '2.0.0',
                        'request': 'GetFeature',
                        'typeName': 'bag:pand',
                        'srsName': 'EPSG:28992',
                        'outputFormat': 'application/json',
                        'count': 3,
                        'bbox': f"{amsterdam_bbox[0]},{amsterdam_bbox[1]},{amsterdam_bbox[2]},{amsterdam_bbox[3]},EPSG:28992"
                    }
                    
                    print(f"Testing with known Amsterdam coordinates: {params_test}")
                    
                    try:
                        response_test = requests.get(self.base_url, params=params_test, timeout=30)
                        response_test.raise_for_status()
                        data_test = response_test.json()
                        test_features = data_test.get('features', [])
                        
                        print(f"Amsterdam test returned {len(test_features)} features")
                        
                        if test_features:
                            print("PDOK service is working! The issue is with coordinate conversion.")
                            # Try to use the working coordinates approach for the actual location
                            if location:
                                loc_data = find_location_coordinates(location)
                                if "error" not in loc_data and self.transformer_to_rd:
                                    lat, lon = loc_data["lat"], loc_data["lon"]
                                    center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                                    
                                    # Create a proper RD New bbox
                                    buffer = 1000  # 1km radius
                                    location_bbox = [
                                        center_x - buffer,
                                        center_y - buffer,
                                        center_x + buffer,
                                        center_y + buffer
                                    ]
                                    
                                    params_fixed = {
                                        'service': 'WFS',
                                        'version': '2.0.0',
                                        'request': 'GetFeature',
                                        'typeName': 'bag:pand',
                                        'srsName': 'EPSG:28992',
                                        'outputFormat': 'application/json',
                                        'count': max_features,
                                        'bbox': f"{location_bbox[0]},{location_bbox[1]},{location_bbox[2]},{location_bbox[3]},EPSG:28992"
                                    }
                                    
                                    print(f"Trying with fixed coordinates for {location}: {params_fixed}")
                                    
                                    response_fixed = requests.get(self.base_url, params=params_fixed, timeout=30)
                                    response_fixed.raise_for_status()
                                    data_fixed = response_fixed.json()
                                    raw_features = data_fixed.get('features', [])
                                    
                                    print(f"Fixed coordinates returned {len(raw_features)} features")
                        else:
                            print("PDOK service test failed - may be a service issue")
                            
                    except Exception as test_error:
                        print(f"PDOK test failed: {test_error}")
            
            if not raw_features:
                print("No real PDOK data found after all attempts - using mock data as fallback")
                mock_tool = MockBuildingTool()
                return mock_tool.forward(location or "Groningen", max_features)
            
            # Process features
            processed_features = []
            
            for i, feature in enumerate(raw_features):
                try:
                    props = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    print(f"Processing feature {i+1}/{len(raw_features)}")
                    
                    if not geometry:
                        print(f"  Feature {i} has no geometry, skipping")
                        continue
                    
                    # Calculate basic properties
                    building_id = props.get('identificatie', f'Building_{i+1}')
                    building_year = props.get('bouwjaar', 'Unknown')
                    building_status = props.get('status', 'Unknown')
                    
                    print(f"  Building ID: {building_id}")
                    print(f"  Year: {building_year}")
                    print(f"  Status: {building_status}")
                    
                    # Create simple centroid calculation for polygon
                    if geometry.get('type') == 'Polygon' and geometry.get('coordinates'):
                        coords = geometry['coordinates'][0]  # Exterior ring
                        if coords and len(coords) > 0:
                            # Calculate centroid
                            avg_lon = sum(coord[0] for coord in coords) / len(coords)
                            avg_lat = sum(coord[1] for coord in coords) / len(coords)
                            
                            print(f"  Original centroid: {avg_lon}, {avg_lat}")
                            
                            # Convert to WGS84 if needed
                            if self.transformer_to_wgs84 and use_rd_coordinates:
                                try:
                                    avg_lon, avg_lat = self.transformer_to_wgs84.transform(avg_lon, avg_lat)
                                    print(f"  Converted to WGS84: {avg_lon}, {avg_lat}")
                                except Exception as transform_error:
                                    print(f"  Coordinate transformation failed: {transform_error}")
                        else:
                            avg_lon, avg_lat = 0, 0
                            print(f"  No valid coordinates found")
                    else:
                        avg_lon, avg_lat = 0, 0
                        print(f"  Not a polygon or no coordinates")
                    
                    # Calculate area (simple approximation)
                    area_m2 = 0
                    if geometry.get('type') == 'Polygon' and geometry.get('coordinates'):
                        try:
                            from shapely.geometry import shape
                            geom = shape(geometry)
                            area_m2 = round(geom.area, 2)
                            print(f"  Calculated area: {area_m2}m²")
                            
                            # Convert entire geometry to WGS84 if needed
                            if self.transformer_to_wgs84 and use_rd_coordinates:
                                from shapely.ops import transform
                                geom_wgs84 = transform(self.transformer_to_wgs84.transform, geom)
                                geometry = geom_wgs84.__geo_interface__
                                print(f"  Geometry converted to WGS84")
                                
                                # Ensure coordinates are proper lists (not tuples)
                                def ensure_lists(obj):
                                    if isinstance(obj, (list, tuple)):
                                        return [ensure_lists(item) for item in obj]
                                    return obj
                                
                                if 'coordinates' in geometry:
                                    geometry['coordinates'] = ensure_lists(geometry['coordinates'])
                                    print(f"  Coordinates converted to lists")
                                    
                        except ImportError:
                            area_m2 = 100  # Default area if shapely not available
                            print(f"  Shapely not available - using default area")
                        except Exception as area_error:
                            area_m2 = 0
                            print(f"  Area calculation failed: {area_error}")
                    
                    # Apply area filter if specified
                    if min_area and area_m2 < min_area:
                        print(f"  Building filtered out - area {area_m2} < {min_area}")
                        continue
                    
                    print(f"  Building accepted - area {area_m2} >= {min_area or 0}")
                    
                    # Create descriptive name
                    building_name = f"Building {building_id[-6:]}" if len(building_id) > 6 else building_id
                    if building_year and building_year != 'Unknown':
                        building_name += f" ({building_year})"
                    
                    # Build description
                    desc_parts = []
                    if building_year and building_year != 'Unknown':
                        desc_parts.append(f"Built: {building_year}")
                    if building_status and building_status != 'Unknown':
                        desc_parts.append(f"Status: {building_status}")
                    if area_m2 > 0:
                        desc_parts.append(f"Area: {area_m2}m²")
                    
                    num_units = props.get('aantal_verblijfsobjecten')
                    if num_units:
                        desc_parts.append(f"Units: {num_units}")
                    
                    description = " | ".join(desc_parts) if desc_parts else "Dutch building from PDOK database"
                    
                    # Create enhanced feature object
                    enhanced_feature = {
                        "name": building_name,
                        "lat": avg_lat,
                        "lon": avg_lon,
                        "description": description,
                        "geometry": geometry,
                        "properties": {
                            **props,
                            "area_m2": area_m2,
                            "centroid_lat": avg_lat,
                            "centroid_lon": avg_lon,
                        }
                    }
                    
                    processed_features.append(enhanced_feature)
                    print(f"  Successfully processed building: {building_name}")
                    
                except Exception as feature_error:
                    print(f"  Error processing feature {i}: {feature_error}")
                    continue
            
            if not processed_features:
                print("No valid buildings found after processing - using mock data")
                mock_tool = MockBuildingTool()
                return mock_tool.forward(location or "Groningen", max_features)
            
            # Sort by area (largest first)
            processed_features.sort(key=lambda x: x['properties'].get('area_m2', 0), reverse=True)
            
            print(f"\n=== FINAL RESULT ===")
            print(f"Successfully processed {len(processed_features)} buildings")
            
            for i, building in enumerate(processed_features[:3]):  # Show first 3
                print(f"Building {i+1}:")
                print(f"  Name: {building['name']}")
                print(f"  Coordinates: {building['lat']:.6f}, {building['lon']:.6f}")
                print(f"  Description: {building['description']}")
                print(f"  Geometry type: {building['geometry'].get('type', 'Unknown')}")
            
            print(f"=== END DEBUG ===\n")
            
            return processed_features
            
        except requests.RequestException as e:
            error_msg = f"HTTP request to PDOK failed: {str(e)}"
            print(f"REQUEST ERROR: {error_msg}")
            # Try mock data as fallback
            mock_tool = MockBuildingTool()
            return mock_tool.forward(location or "Groningen", max_features)
        except Exception as e:
            error_msg = f"PDOK Buildings tool error: {str(e)}"
            print(f"TOOL ERROR: {error_msg}")
            # Try mock data as fallback
            mock_tool = MockBuildingTool()
            return mock_tool.forward(location or "Groningen", max_features)

# Simple PDOK Test Tool
class SimplePDOKTestTool(Tool):
    """Simple tool to test PDOK with known working coordinates"""
    
    name = "test_pdok_simple"
    description = "Test PDOK service with known working coordinates for debugging"
    inputs = {
        "city": {
            "type": "string",
            "description": "City name (e.g., 'Amsterdam', 'Groningen')",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, city="Amsterdam"):
        """Test PDOK with known coordinates"""
        try:
            print(f"\n=== SIMPLE PDOK TEST for {city} ===")
            
            # Known working coordinates for major Dutch cities
            city_coords = {
                "amsterdam": {"lat": 52.3676, "lon": 4.9041, "rd_x": 121000, "rd_y": 487000},
                "rotterdam": {"lat": 51.9225, "lon": 4.4792, "rd_x": 92000, "rd_y": 438000},
                "utrecht": {"lat": 52.0907, "lon": 5.1214, "rd_x": 136000, "rd_y": 455000},
                "groningen": {"lat": 53.2194, "lon": 6.5665, "rd_x": 235000, "rd_y": 582000},
                "den haag": {"lat": 52.0705, "lon": 4.3007, "rd_x": 82000, "rd_y": 454000}
            }
            
            city_lower = city.lower()
            if city_lower not in city_coords:
                city_lower = "amsterdam"  # Default fallback
            
            coords = city_coords[city_lower]
            print(f"Using coordinates for {city_lower}: {coords}")
            
            # Create tight bounding box around city center (500m radius)
            center_x, center_y = coords["rd_x"], coords["rd_y"]
            buffer = 500  # 500 meter radius
            bbox = [
                center_x - buffer,
                center_y - buffer,
                center_x + buffer,
                center_y + buffer
            ]
            
            print(f"RD New bbox (500m radius): {bbox}")
            
            # Simple WFS request without filters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': 'bag:pand',
                'srsName': 'EPSG:28992',
                'outputFormat': 'application/json',
                'count': 5,
                'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
            }
            
            print(f"Request parameters: {params}")
            
            response = requests.get("https://service.pdok.nl/lv/bag/wfs/v2_0", params=params, timeout=30)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            print(f"Response length: {len(response.text)}")
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"Raw features found: {len(features)}")
            
            if not features:
                print("No features found with tight bbox - trying larger area")
                
                # Try with 2km radius
                buffer = 2000
                bbox = [center_x - buffer, center_y - buffer, center_x + buffer, center_y + buffer]
                params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
                
                response = requests.get("https://service.pdok.nl/lv/bag/wfs/v2_0", params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                features = data.get('features', [])
                
                print(f"Features with 2km radius: {len(features)}")
            
            if features:
                print(f"\n=== PROCESSING REAL PDOK DATA ===")
                processed = []
                
                for i, feature in enumerate(features[:5]):  # Limit to 5
                    props = feature.get('properties', {})
                    geom = feature.get('geometry', {})
                    
                    print(f"\nFeature {i+1}:")
                    print(f"  Properties: {list(props.keys())}")
                    print(f"  Geometry type: {geom.get('type', 'None')}")
                    
                    # Convert geometry to WGS84 for map display
                    if geom and geom.get('type') == 'Polygon':
                        try:
                            import pyproj
                            transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
                            
                            # Convert polygon coordinates
                            rd_coords = geom['coordinates'][0]  # Exterior ring
                            wgs84_coords = []
                            
                            for coord in rd_coords:
                                lon, lat = transformer.transform(coord[0], coord[1])
                                wgs84_coords.append([lon, lat])
                            
                            # Calculate centroid
                            avg_lon = sum(c[0] for c in wgs84_coords) / len(wgs84_coords)
                            avg_lat = sum(c[1] for c in wgs84_coords) / len(wgs84_coords)
                            
                            # Create building object
                            building = {
                                "name": f"Real Building {props.get('identificatie', '')[-6:]} ({props.get('bouwjaar', 'Unknown')})",
                                "lat": avg_lat,
                                "lon": avg_lon,
                                "description": f"Real PDOK building | Built: {props.get('bouwjaar', 'Unknown')} | Status: {props.get('status', 'Unknown')}",
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [wgs84_coords]
                                },
                                "properties": props
                            }
                            
                            processed.append(building)
                            print(f"  Converted to WGS84 - Center: {avg_lat:.6f}, {avg_lon:.6f}")
                            print(f"  Polygon points: {len(wgs84_coords)}")
                            
                        except Exception as e:
                            print(f"  Error processing geometry: {e}")
                
                if processed:
                    print(f"\n=== SUCCESS: {len(processed)} real buildings processed ===")
                    return processed
                else:
                    print("No buildings could be processed")
            
            # Fallback to mock data
            print("Using mock data as fallback")
            mock_tool = MockBuildingTool()
            return mock_tool.forward(city, 5)
            
        except Exception as e:
            print(f"PDOK test error: {e}")
            mock_tool = MockBuildingTool()
            return mock_tool.forward(city, 5)

# Direct Return Tool (bypass agent restructuring)
class DirectReturnTool(Tool):
    """Tool to return building data directly without restructuring"""
    
    name = "return_buildings_directly"
    description = "Return building data directly to the frontend without any restructuring to preserve coordinates and geometry."
    inputs = {
        "buildings": {
            "type": "array",
            "description": "List of building objects with proper coordinates and geometry",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, buildings=None):
        """Return buildings directly without any processing"""
        try:
            if not buildings:
                return [{"error": "No buildings provided"}]
            
            print(f"\n=== DIRECT RETURN TOOL ===")
            print(f"Returning {len(buildings)} buildings directly without modification")
            
            # Validate that we have good data
            valid_buildings = []
            for building in buildings:
                if isinstance(building, dict):
                    lat = building.get('lat', 0)
                    lon = building.get('lon', 0)
                    if lat != 0 and lon != 0:
                        valid_buildings.append(building)
                        print(f"  Valid building: {building.get('name', 'Unknown')} at {lat:.6f}, {lon:.6f}")
                    else:
                        print(f"  Invalid building: {building.get('name', 'Unknown')} at {lat}, {lon}")
            
            if valid_buildings:
                print(f"Returning {len(valid_buildings)} valid buildings")
                return valid_buildings
            else:
                return [{"error": "No buildings with valid coordinates found"}]
                
        except Exception as e:
            error_msg = f"Direct return error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]

# Quick Buildings Tool (No area filtering)
class QuickBuildingsTool(Tool):
    """Quick tool to get buildings without area filtering"""
    
    name = "get_buildings_quick"
    description = "Get buildings from a location quickly without area restrictions - includes all building sizes."
    inputs = {
        "location": {
            "type": "string",
            "description": "Location name (e.g., 'Groningen', 'Amsterdam')",
            "nullable": True
        },
        "count": {
            "type": "integer",
            "description": "Number of buildings to return (default: 5)",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, location=None, count=5):
        """Get buildings quickly without area filtering"""
        try:
            print(f"\n=== QUICK BUILDINGS TOOL ===")
            print(f"Location: {location}, Count: {count}")
            
            if not location:
                return [{"error": "Location is required"}]
            
            # Use the advanced PDOK tool but with no area filtering
            pdok_tool = PDOKBuildingsAdvancedTool()
            result = pdok_tool.forward(
                location=location,
                max_features=count,
                min_area=None,  # No area filtering!
                radius_km=2.0   # Slightly larger search area
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Quick buildings error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]

# Smart Building Search Tool
class BuildingSearchTool(Tool):
    """Smart building search tool with natural language processing"""
    
    name = "search_buildings"
    description = "Search for buildings using natural language queries like 'historic buildings in Amsterdam' or '5 large buildings in Groningen'."
    inputs = {
        "query": {
            "type": "string",
            "description": "Natural language search query (e.g., 'historic buildings in Amsterdam', '5 large buildings in Groningen')"
        }
    }
    output_type = "array" 
    is_initialized = True
    
    def forward(self, query):
        """Parse search query and call PDOK tool with appropriate filters."""
        try:
            query_lower = query.lower()
            print(f"Parsing building search query: {query}")
            
            # Extract location
            location = None
            for word in ['in', 'near', 'around', 'at']:
                if word in query_lower:
                    parts = query_lower.split(word, 1)
                    if len(parts) > 1:
                        location = parts[1].strip()
                        break
            
            if not location:
                # Try to find common Dutch city names
                cities = ['amsterdam', 'rotterdam', 'utrecht', 'groningen', 'eindhoven', 'tilburg', 'almere', 'breda', 'nijmegen']
                for city in cities:
                    if city in query_lower:
                        location = city
                        break
            
            # Extract number of buildings
            max_features = 10  # default
            import re
            numbers = re.findall(r'\d+', query)
            if numbers:
                max_features = min(int(numbers[0]), 50)  # Cap at 50
            
            # Determine filters based on query keywords
            filters = {}
            
            if any(word in query_lower for word in ['historic', 'historical', 'old', 'ancient']):
                filters['max_year'] = 1945
                filters['radius_km'] = 2.0
                filters['min_area'] = 20  # Lower threshold for historic buildings
            elif any(word in query_lower for word in ['modern', 'new', 'recent', 'contemporary']):
                filters['min_year'] = 2000
                filters['radius_km'] = 2.0
                filters['min_area'] = 20  # Lower threshold for modern buildings
            elif any(word in query_lower for word in ['large', 'big', 'huge', 'massive']):
                filters['min_area'] = 500
                filters['radius_km'] = 3.0
            elif any(word in query_lower for word in ['small', 'tiny', 'compact']):
                filters['min_area'] = 10  # Very low threshold for small buildings
                filters['radius_km'] = 1.0
            elif 'center' in query_lower or 'centre' in query_lower:
                filters['radius_km'] = 0.5
                filters['min_area'] = 20  # Lower threshold for city center
            else:
                # Default case - use low threshold to get more buildings
                filters['min_area'] = 20  # Reduced from default to get more results
            
            if not location:
                return [{"error": "Could not identify location in query. Please specify a city or area."}]
            
            print(f"Extracted: location='{location}', max_features={max_features}, filters={filters}")
            
            # Use the advanced PDOK tool
            pdok_tool = PDOKBuildingsAdvancedTool()
            result = pdok_tool.forward(
                location=location,
                max_features=max_features,
                **filters
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Building search error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]

# Mock Building Tool (Fallback)
class MockBuildingTool(Tool):
    """Mock tool for sample building data when real data is unavailable"""
    
    name = "get_sample_buildings"
    description = "Get sample building data for demonstration when real PDOK data is unavailable."
    inputs = {
        "location": {
            "type": "string", 
            "description": "Location name (e.g., 'Groningen')"
        },
        "count": {
            "type": "integer",
            "description": "Number of sample buildings (default: 5)",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, location, count=5):
        """Generate sample building data for the specified location."""
        try:
            # Get real coordinates for the location
            loc_data = find_location_coordinates(location)
            if "error" in loc_data:
                return [{"error": loc_data["error"]}]
            
            base_lat, base_lon = loc_data["lat"], loc_data["lon"]
            
            # Sample building data
            sample_buildings = [
                {
                    "name": "Historic Building 1851",
                    "lat": base_lat + 0.001,
                    "lon": base_lon + 0.002,
                    "description": "Built in 1851 | Status: In use | Area: 245m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[base_lon + 0.002, base_lat + 0.001], 
                                        [base_lon + 0.0022, base_lat + 0.001], 
                                        [base_lon + 0.0022, base_lat + 0.0012], 
                                        [base_lon + 0.002, base_lat + 0.0012], 
                                        [base_lon + 0.002, base_lat + 0.001]]]
                    },
                    "properties": {"bouwjaar": "1851", "status": "Pand in gebruik", "area_m2": 245}
                },
                {
                    "name": "Modern Office 2018",
                    "lat": base_lat - 0.001,
                    "lon": base_lon - 0.001,
                    "description": "Built in 2018 | Status: In use | Area: 1250m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[base_lon - 0.001, base_lat - 0.001], 
                                        [base_lon - 0.0008, base_lat - 0.001], 
                                        [base_lon - 0.0008, base_lat - 0.0008], 
                                        [base_lon - 0.001, base_lat - 0.0008], 
                                        [base_lon - 0.001, base_lat - 0.001]]]
                    },
                    "properties": {"bouwjaar": "2018", "status": "Pand in gebruik", "area_m2": 1250}
                },
                {
                    "name": "Traditional House 1923",
                    "lat": base_lat + 0.002,
                    "lon": base_lon - 0.002,
                    "description": "Built in 1923 | Status: In use | Area: 156m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[base_lon - 0.002, base_lat + 0.002], 
                                        [base_lon - 0.0018, base_lat + 0.002], 
                                        [base_lon - 0.0018, base_lat + 0.0022], 
                                        [base_lon - 0.002, base_lat + 0.0022], 
                                        [base_lon - 0.002, base_lat + 0.002]]]
                    },
                    "properties": {"bouwjaar": "1923", "status": "Pand in gebruik", "area_m2": 156}
                },
                {
                    "name": "Shopping Center 1987",
                    "lat": base_lat - 0.002,
                    "lon": base_lon + 0.001,
                    "description": "Built in 1987 | Status: In use | Area: 3400m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[base_lon + 0.001, base_lat - 0.002], 
                                        [base_lon + 0.0015, base_lat - 0.002], 
                                        [base_lon + 0.0015, base_lat - 0.0015], 
                                        [base_lon + 0.001, base_lat - 0.0015], 
                                        [base_lon + 0.001, base_lat - 0.002]]]
                    },
                    "properties": {"bouwjaar": "1987", "status": "Pand in gebruik", "area_m2": 3400}
                },
                {
                    "name": "University Building 1965",
                    "lat": base_lat + 0.0015,
                    "lon": base_lon + 0.0015,
                    "description": "Built in 1965 | Status: In use | Area: 890m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[base_lon + 0.0015, base_lat + 0.0015], 
                                        [base_lon + 0.0018, base_lat + 0.0015], 
                                        [base_lon + 0.0018, base_lat + 0.0018], 
                                        [base_lon + 0.0015, base_lat + 0.0018], 
                                        [base_lon + 0.0015, base_lat + 0.0015]]]
                    },
                    "properties": {"bouwjaar": "1965", "status": "Pand in gebruik", "area_m2": 890}
                }
            ]
            
            # Return requested number of buildings
            buildings = sample_buildings[:count]
            print(f"Generated {len(buildings)} sample buildings for {location}")
            return buildings
            
        except Exception as e:
            error_msg = f"Mock building tool error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]

# Final Answer Tool for proper frontend integration
class FinalAnswerTool(Tool):
    """Tool to format and return final building data to the frontend"""
    
    name = "final_answer"
    description = "Return the final building data in the correct format for the map frontend."
    inputs = {
        "buildings": {
            "type": "array",
            "description": "List of building objects to display on the map"
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, buildings):
        """Format and return buildings for the frontend map."""
        try:
            if not buildings:
                return [{"error": "No buildings to display"}]
            
            # Ensure each building has the required format for the frontend
            formatted_buildings = []
            
            for building in buildings:
                if isinstance(building, dict) and 'error' not in building:
                    
                    # Check if this is already properly formatted PDOK data
                    if all(key in building for key in ['name', 'lat', 'lon', 'geometry', 'properties']):
                        # Already properly formatted - just validate coordinates
                        lat = building.get('lat', 0)
                        lon = building.get('lon', 0)
                        
                        if lat != 0 and lon != 0:  # Valid coordinates
                            formatted_buildings.append(building)
                            continue
                    
                    # Handle manually created data structures from agent
                    if 'coordinates' in building:
                        coords = building['coordinates']
                        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                            lat, lon = coords[0], coords[1]
                        else:
                            lat, lon = 0, 0
                    else:
                        lat = building.get('lat', 0)
                        lon = building.get('lon', 0)
                    
                    # Create formatted building
                    formatted_building = {
                        "name": building.get("name", "Unknown Building"),
                        "lat": float(lat) if lat != 0 else 0.0,
                        "lon": float(lon) if lon != 0 else 0.0,
                        "description": building.get("description", "Building information"),
                        "geometry": building.get("geometry", {
                            "type": "Point",
                            "coordinates": [lon, lat] if lat != 0 and lon != 0 else [0, 0]
                        }),
                        "properties": building.get("properties", {})
                    }
                    
                    formatted_buildings.append(formatted_building)
            
            print(f"Final answer: returning {len(formatted_buildings)} formatted buildings")
            
            # Log sample for debugging
            if formatted_buildings:
                sample = formatted_buildings[0]
                print(f"Sample building: {sample['name']}")
                print(f"  Coordinates: {sample['lat']}, {sample['lon']}")
                print(f"  Geometry type: {sample['geometry'].get('type', 'Unknown')}")
            
            return formatted_buildings
            
        except Exception as e:
            error_msg = f"Final answer error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]

# Map Content Understanding Tool
class MapContentUnderstandingTool(Tool):
    """Tool to analyze and describe map content"""
    
    name = "describe_map_content"
    description = "Describes the content currently displayed on the map."
    inputs = {
        "features": {
            "type": "array", 
            "description": "List of features currently displayed on the map"
        }
    }
    output_type = "string"
    is_initialized = True

    def forward(self, features):
        """Analyze and describe the features displayed on the map."""
        try:
            if not features or any("error" in str(f) for f in features):
                return "No valid features on the map."
            
            feature_types = {}
            total_area = 0
            years = []
            
            for f in features:
                if isinstance(f, dict):
                    props = f.get("properties", {})
                    f_type = props.get("type", "building")
                    feature_types[f_type] = feature_types.get(f_type, 0) + 1
                    
                    # Collect area data
                    area = props.get("area_m2", 0)
                    if area > 0:
                        total_area += area
                    
                    # Collect year data
                    year = props.get("bouwjaar")
                    if year and str(year).isdigit():
                        years.append(int(year))
            
            description = f"Map contains {len(features)} buildings:\n"
            
            # Building types
            for f_type, count in feature_types.items():
                description += f"- {count} {f_type} buildings\n"
            
            # Area statistics
            if total_area > 0:
                avg_area = total_area / len(features)
                description += f"\nTotal area: {total_area:,.0f} m²\n"
                description += f"Average area: {avg_area:.0f} m²\n"
            
            # Year statistics
            if years:
                oldest = min(years)
                newest = max(years)
                description += f"\nAge range: {oldest} - {newest}\n"
                description += f"Average construction year: {sum(years) // len(years)}\n"
            
            return description
            
        except Exception as e:
            return f"Error describing map: {str(e)}"

# Initialize agent with clean tool list including direct return tool
agent = CodeAgent(
    model=model,
    tools=[
        find_location_coordinates,        # Location search
        QuickBuildingsTool(),            # Quick building search (no area filter)
        DirectReturnTool(),              # Direct return (bypass restructuring)
        SimplePDOKTestTool(),            # Simple PDOK test with known coordinates
        PDOKBuildingsAdvancedTool(),     # Primary PDOK tool
        BuildingSearchTool(),            # Smart query parser  
        MockBuildingTool(),              # Fallback sample data
        MapContentUnderstandingTool(),   # Map content analysis
        FinalAnswerTool(),              # Format final answer for frontend
        DuckDuckGoSearchTool()

    ],
    max_steps=15,
    additional_authorized_imports=[
        "xml.etree.ElementTree", 
        "json", 
        "requests", 
        "shapely.geometry", 
        "shapely.ops", 
        "pyproj",
        "re"
    ]
)
agent.logger.console.width = 66

# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    print("Serving index route")
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries from the frontend."""
    print("\n" + "="*60)
    print("RECEIVED QUERY REQUEST")
    print("="*60)
    
    data = request.json
    query_text = data.get('query', '')
    current_features = data.get('current_features', [])
    
    print(f"Query text: {query_text}")
    print(f"Current features count: {len(current_features)}")
    
    try:
        print("Running agent...")
        result = agent.run(query_text)
        
        print(f"\n--- AGENT RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        print(f"Result value: {result}")
        
        # Handle different result types
        if hasattr(result, '__dict__'):
            print(f"Result attributes: {vars(result)}")
        
        # Try to extract actual data
        actual_data = None
        
        if hasattr(result, 'content') or hasattr(result, 'text'):
            # Extract text content if it's an agent response object
            text_content = getattr(result, 'content', None) or getattr(result, 'text', None)
            print(f"Text content: {text_content}")
            
            # Try to parse as JSON if it looks like building data
            if text_content and ('[{' in str(text_content) or 'Building' in str(text_content)):
                try:
                    import json
                    actual_data = json.loads(str(text_content))
                    print(f"Parsed JSON from text: {actual_data}")
                except:
                    print("Could not parse text as JSON")
        
        # Check if result is directly usable data
        if isinstance(result, list):
            actual_data = result
            print(f"Result is already a list with {len(result)} items")
        elif isinstance(result, dict):
            actual_data = result
            print(f"Result is a dict with keys: {list(result.keys())}")
        
        # Try to find building data in agent's execution history
        if not actual_data and hasattr(agent, 'logs'):
            print("Searching agent logs for building data...")
            for log_entry in reversed(agent.logs):
                if hasattr(log_entry, 'step_logs'):
                    for step_log in log_entry.step_logs:
                        if hasattr(step_log, 'tool_calls'):
                            for tool_call in step_log.tool_calls:
                                if (hasattr(tool_call, 'result') and 
                                    isinstance(tool_call.result, list) and
                                    tool_call.result and 
                                    isinstance(tool_call.result[0], dict)):
                                    
                                    first_result = tool_call.result[0]
                                    # Check if this is good PDOK building data
                                    if ('name' in first_result and 'lat' in first_result and 
                                        'lon' in first_result and 'geometry' in first_result and
                                        first_result.get('lat', 0) != 0 and first_result.get('lon', 0) != 0):
                                        actual_data = tool_call.result
                                        print(f"Found good PDOK building data in step logs: {len(actual_data)} buildings")
                                        print(f"  Sample coordinates: {first_result.get('lat')}, {first_result.get('lon')}")
                                        break
                        if actual_data:
                            break
                if actual_data:
                    break
        
        # Also check the direct agent logs structure
        if not actual_data and hasattr(agent, 'logs'):
            print("Searching direct agent logs...")
            for log_entry in agent.logs:
                if hasattr(log_entry, 'tool_calls'):
                    for tool_call in log_entry.tool_calls:
                        if (hasattr(tool_call, 'result') and 
                            isinstance(tool_call.result, list) and
                            tool_call.result and 
                            isinstance(tool_call.result[0], dict)):
                            
                            first_result = tool_call.result[0]
                            # Check if this is good PDOK building data
                            if ('name' in first_result and 'lat' in first_result and 
                                'lon' in first_result and 'geometry' in first_result and
                                first_result.get('lat', 0) != 0 and first_result.get('lon', 0) != 0):
                                actual_data = tool_call.result
                                print(f"Found good PDOK building data in direct logs: {len(actual_data)} buildings")
                                print(f"  Sample coordinates: {first_result.get('lat')}, {first_result.get('lon')}")
                                break
                if actual_data:
                    break
        
        print(f"\n--- FINAL DATA TO RETURN ---")
        
        if actual_data:
            print(f"Returning data type: {type(actual_data)}")
            if isinstance(actual_data, list):
                print(f"List length: {len(actual_data)}")
                if actual_data and isinstance(actual_data[0], dict):
                    first_item = actual_data[0]
                    print(f"First item keys: {list(first_item.keys())}")
                    print(f"First item sample: {dict(list(first_item.items())[:3])}")
                    
                    # Check if it's building data
                    required_keys = ['name', 'lat', 'lon', 'geometry']
                    has_building_data = all(key in first_item for key in required_keys)
                    print(f"Has building data format: {has_building_data}")
                    
                    if has_building_data:
                        print("\n--- BUILDING DATA PREVIEW ---")
                        for i, building in enumerate(actual_data[:2]):  # Show first 2
                            print(f"Building {i+1}:")
                            print(f"  Name: {building.get('name', 'N/A')}")
                            print(f"  Coordinates: {building.get('lat', 'N/A')}, {building.get('lon', 'N/A')}")
                            print(f"  Geometry type: {building.get('geometry', {}).get('type', 'N/A')}")
                            print(f"  Description: {building.get('description', 'N/A')[:100]}...")
            
            print(f"Returning actual_data to frontend")
            response_data = actual_data
        else:
            print(f"No building data found, returning original result")
            response_data = str(result) if not isinstance(result, (dict, list)) else result
        
        print(f"\n--- RESPONSE TO FRONTEND ---")
        print(f"Response data type: {type(response_data)}")
        print(f"Response preview: {str(response_data)[:200]}...")
        
        print("="*60)
        print("END QUERY PROCESSING")
        print("="*60 + "\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Agent error: {str(e)}"
        print(f"ERROR: {error_msg}")
        print("="*60 + "\n")
        return jsonify({"error": error_msg})

if __name__ == '__main__':
    print("Starting Flask server")
    print("Available tools:")
    #for tool in agent.tools:
        #print(f"  - {tool.name}: {tool.description}")
    app.run(debug=True, port=5000)