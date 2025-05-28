# app.py - Map-Aware PDOK Web Map Chat Assistant
import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool, Tool, DuckDuckGoSearchTool
import statistics
from collections import Counter
from datetime import datetime


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

# Global variable to store current map state
current_map_state = {
    "features": [],
    "center": [5.2913, 52.1326],  # Netherlands center
    "zoom": 8,
    "view_bounds": None,
    "last_updated": None,
    "statistics": {}
}

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

@tool
def analyze_current_map_features() -> dict:
    """
    Analyzes the features currently displayed on the map and provides statistics and insights.
    
    Returns:
        dict: Analysis of current map features including counts, statistics, and insights.
    """
    try:
        global current_map_state
        features = current_map_state.get("features", [])
        
        if not features:
            return {
                "message": "No features are currently displayed on the map.",
                "feature_count": 0,
                "suggestions": ["Try searching for buildings in a specific location like 'Amsterdam' or 'Groningen'"]
            }
        
        analysis = {
            "feature_count": len(features),
            "feature_types": {},
            "building_statistics": {},
            "geographic_info": {},
            "temporal_analysis": {},
            "summary": ""
        }
        
        # Analyze feature types and geometry
        geometry_types = []
        building_years = []
        building_areas = []
        locations = []
        
        for feature in features:
            # Geometry analysis
            if 'geometry' in feature and feature['geometry']:
                geom_type = feature['geometry'].get('type', 'Unknown')
                geometry_types.append(geom_type)
            
            # Extract properties
            props = feature.get('properties', {})
            
            # Building year analysis
            year = props.get('bouwjaar')
            if year and str(year).isdigit():
                building_years.append(int(year))
            
            # Area analysis
            area = props.get('area_m2', 0)
            if area > 0:
                building_areas.append(area)
            
            # Location tracking
            if 'lat' in feature and 'lon' in feature:
                locations.append((feature['lat'], feature['lon']))
        
        # Feature type statistics
        analysis["feature_types"] = dict(Counter(geometry_types))
        
        # Building statistics
        if building_years:
            analysis["building_statistics"]["year_range"] = {
                "oldest": min(building_years),
                "newest": max(building_years),
                "average": round(statistics.mean(building_years)),
                "median": round(statistics.median(building_years))
            }
            
            # Categorize by era
            historic = sum(1 for y in building_years if y < 1900)
            early_modern = sum(1 for y in building_years if 1900 <= y < 1950)
            mid_century = sum(1 for y in building_years if 1950 <= y < 2000)
            contemporary = sum(1 for y in building_years if y >= 2000)
            
            analysis["building_statistics"]["era_distribution"] = {
                "historic_pre_1900": historic,
                "early_modern_1900_1950": early_modern,
                "mid_century_1950_2000": mid_century,
                "contemporary_post_2000": contemporary
            }
        
        if building_areas:
            analysis["building_statistics"]["area_stats"] = {
                "total_area_m2": round(sum(building_areas)),
                "average_area_m2": round(statistics.mean(building_areas)),
                "largest_building_m2": max(building_areas),
                "smallest_building_m2": min(building_areas)
            }
        
        # Geographic analysis
        if locations:
            lats = [loc[0] for loc in locations]
            lons = [loc[1] for loc in locations]
            
            analysis["geographic_info"] = {
                "center_point": [round(statistics.mean(lats), 6), round(statistics.mean(lons), 6)],
                "bounding_box": {
                    "north": max(lats),
                    "south": min(lats),
                    "east": max(lons),
                    "west": min(lons)
                },
                "spread_km": round(((max(lats) - min(lats)) * 111), 2)  # Rough km conversion
            }
        
        # Generate summary
        summary_parts = []
        summary_parts.append(f"Currently displaying {len(features)} features on the map")
        
        if analysis["feature_types"]:
            geom_desc = ", ".join([f"{count} {geom_type.lower()}{'s' if count > 1 else ''}" 
                                 for geom_type, count in analysis["feature_types"].items()])
            summary_parts.append(f"Geometry types: {geom_desc}")
        
        if building_years:
            year_stats = analysis["building_statistics"]["year_range"]
            summary_parts.append(f"Buildings span from {year_stats['oldest']} to {year_stats['newest']} (average: {year_stats['average']})")
        
        if building_areas:
            area_stats = analysis["building_statistics"]["area_stats"]
            summary_parts.append(f"Total building area: {area_stats['total_area_m2']:,}m² across {len(building_areas)} buildings")
        
        analysis["summary"] = ". ".join(summary_parts) + "."
        
        # Update global state
        current_map_state["statistics"] = analysis
        current_map_state["last_updated"] = datetime.now().isoformat()
        
        return analysis
        
    except Exception as e:
        return {"error": f"Error analyzing map features: {str(e)}"}

@tool
def get_map_context_info() -> dict:
    """
    Provides information about the current map view, center, and context.
    
    Returns:
        dict: Current map context including center point, zoom level, and view area.
    """
    try:
        global current_map_state
        
        context = {
            "current_center": current_map_state.get("center", [5.2913, 52.1326]),
            "current_zoom": current_map_state.get("zoom", 8),
            "feature_count": len(current_map_state.get("features", [])),
            "last_updated": current_map_state.get("last_updated"),
            "view_bounds": current_map_state.get("view_bounds")
        }
        
        # Determine approximate location based on center
        center_lat, center_lon = context["current_center"]
        
        # Rough location detection for Netherlands
        if 50.5 <= center_lat <= 54.0 and 3.0 <= center_lon <= 7.5:
            if 52.3 <= center_lat <= 52.4 and 4.8 <= center_lon <= 5.0:
                context["approximate_location"] = "Amsterdam area"
            elif 51.9 <= center_lat <= 52.0 and 4.4 <= center_lon <= 4.6:
                context["approximate_location"] = "Rotterdam area"
            elif 52.0 <= center_lat <= 52.2 and 5.0 <= center_lon <= 5.2:
                context["approximate_location"] = "Utrecht area"
            elif 53.1 <= center_lat <= 53.3 and 6.4 <= center_lon <= 6.7:
                context["approximate_location"] = "Groningen area"
            else:
                context["approximate_location"] = "Netherlands"
        else:
            context["approximate_location"] = "Unknown area"
        
        return context
        
    except Exception as e:
        return {"error": f"Error getting map context: {str(e)}"}

@tool
def answer_map_question(question: str) -> str:
    """
    Answers general questions about maps, geography, GIS, and spatial analysis.
    
    Args:
        question (str): The map-related question to answer.
        
    Returns:
        str: Answer to the map question.
    """
    try:
        question_lower = question.lower()
        
        # Map concepts and definitions
        if any(term in question_lower for term in ['what is gis', 'geographic information system']):
            return """GIS (Geographic Information System) is a framework for gathering, managing, and analyzing spatial and geographic data. It combines hardware, software, and data to capture, manage, analyze, and display all forms of geographically referenced information. GIS helps us understand patterns, relationships, and trends in our world by connecting location data with descriptive information."""
        
        elif any(term in question_lower for term in ['what is wgs84', 'coordinate system']):
            return """WGS84 (World Geodetic System 1984) is the standard coordinate system used by GPS and most web mapping applications. It defines locations using latitude and longitude in decimal degrees. In the Netherlands, we also use RD New (EPSG:28992), which is the national coordinate system optimized for accurate measurements within Dutch borders."""
        
        elif any(term in question_lower for term in ['what is pdok', 'pdok']):
            return """PDOK (Publieke Dienstverlening Op de Kaart) is the Dutch national spatial data infrastructure. It provides free access to geographic datasets from Dutch government organizations, including building data (BAG), topographic maps, aerial imagery, and administrative boundaries. It's the authoritative source for Dutch geographic information."""
        
        elif any(term in question_lower for term in ['what is bag', 'buildings and addresses']):
            return """BAG (Basisregistratie Adressen en Gebouwen) is the Dutch Buildings and Addresses Database. It contains authoritative information about all buildings, addresses, and premises in the Netherlands. Each building has a unique identifier and includes details like construction year, status, area, and precise polygon geometry."""
        
        elif any(term in question_lower for term in ['projection', 'coordinate projection']):
            return """Map projections transform the curved surface of the Earth onto a flat map. Different projections preserve different properties (area, distance, direction). Web maps typically use Web Mercator (EPSG:3857), while the Netherlands uses RD New (EPSG:28992) for official mapping due to its accuracy within Dutch borders."""
        
        elif any(term in question_lower for term in ['openlayers', 'leaflet', 'web mapping']):
            return """OpenLayers and Leaflet are popular JavaScript libraries for creating interactive web maps. OpenLayers is more feature-rich and handles complex GIS operations, while Leaflet is lighter and easier to use. Both can display various data formats like GeoJSON, WMS, and vector tiles."""
        
        elif any(term in question_lower for term in ['geojson', 'data format']):
            return """GeoJSON is a format for encoding geographic data structures using JSON. It supports points, lines, polygons, and multi-geometries, along with properties for each feature. It's widely used in web mapping because it's human-readable and easily parsed by JavaScript."""
        
        elif any(term in question_lower for term in ['remote sensing', 'satellite']):
            return """Remote sensing involves acquiring information about Earth's surface from satellites or aircraft. Common applications include land use mapping, environmental monitoring, urban planning, and change detection. Satellite imagery provides different spectral bands useful for various analyses."""
        
        elif any(term in question_lower for term in ['spatial analysis', 'spatial query']):
            return """Spatial analysis examines the locations, attributes, and relationships of features in spatial data. Common operations include buffering, overlay analysis, proximity analysis, and spatial statistics. It helps answer questions like 'what's near what' and 'where does it occur'."""
        
        elif any(term in question_lower for term in ['scale', 'map scale']):
            return """Map scale represents the ratio between distance on a map and distance on the ground. Large scale maps (1:1,000) show small areas in detail, while small scale maps (1:1,000,000) show large areas with less detail. Web maps use zoom levels instead of traditional scales."""
        
        elif any(term in question_lower for term in ['topology', 'spatial relationship']):
            return """Topology in GIS describes spatial relationships between features - how they connect, overlap, or relate spatially. Examples include adjacency (features sharing boundaries), containment (one feature inside another), and connectivity (features linked together)."""
        
        else:
            return f"I can help with various map and GIS topics including coordinate systems, data formats, spatial analysis, and Dutch geographic data sources. Could you be more specific about what aspect of mapping or geography you'd like to know about?"
        
    except Exception as e:
        return f"Error answering map question: {str(e)}"

def ensure_json_serializable(obj):
    """Convert any non-JSON serializable objects to JSON serializable format."""
    if isinstance(obj, dict):
        return {key: ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [ensure_json_serializable(item) for item in obj]
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        return [ensure_json_serializable(item) for item in obj]
    elif hasattr(obj, 'item'):
        return obj.item()
    elif hasattr(obj, 'to_dict'):
        return ensure_json_serializable(obj.to_dict())
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        return str(obj)

def validate_and_fix_geometry(geometry):
    """Validate and fix geometry data structure."""
    if not isinstance(geometry, dict):
        return None
        
    geom_type = geometry.get('type')
    coordinates = geometry.get('coordinates')
    
    if not geom_type or not coordinates:
        return None
    
    try:
        fixed_coordinates = ensure_json_serializable(coordinates)
        
        if geom_type == 'Point':
            if not isinstance(fixed_coordinates, list) or len(fixed_coordinates) != 2:
                return None
            if not all(isinstance(coord, (int, float)) for coord in fixed_coordinates):
                return None
                
        elif geom_type == 'Polygon':
            if not isinstance(fixed_coordinates, list) or not fixed_coordinates:
                return None
            exterior = fixed_coordinates[0]
            if not isinstance(exterior, list) or len(exterior) < 4:
                return None
            for coord_pair in exterior:
                if not isinstance(coord_pair, list) or len(coord_pair) != 2:
                    return None
                if not all(isinstance(coord, (int, float)) for coord in coord_pair):
                    return None
                    
        elif geom_type == 'LineString':
            if not isinstance(fixed_coordinates, list) or len(fixed_coordinates) < 2:
                return None
            for coord_pair in fixed_coordinates:
                if not isinstance(coord_pair, list) or len(coord_pair) != 2:
                    return None
                if not all(isinstance(coord, (int, float)) for coord in coord_pair):
                    return None
        
        return {
            'type': geom_type,
            'coordinates': fixed_coordinates
        }
        
    except Exception as e:
        print(f"Error fixing geometry: {e}")
        return None

# Enhanced PDOK Buildings Tool (same as before but with map state updates)
class PDOKBuildingsAdvancedTool(Tool):
    """Advanced PDOK Buildings tool with map state awareness"""
    
    name = "get_pdok_buildings"
    description = "Get detailed building data from PDOK WFS service and update the map state."
    inputs = {
        "location": {"type": "string", "description": "Location name", "nullable": True},
        "bbox": {"type": "array", "description": "Bounding box in RD New coordinates", "nullable": True},
        "max_features": {"type": "integer", "description": "Maximum buildings to return", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "min_area": {"type": "integer", "description": "Minimum building area in m²", "nullable": True},
        "radius_km": {"type": "number", "description": "Search radius in kilometers", "nullable": True}
    }
    output_type = "array"
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
        except ImportError:
            print("Warning: pyproj not available")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, location=None, bbox=None, max_features=10, min_year=None, max_year=None, min_area=None, radius_km=1.0):
        """Get buildings and update map state."""
        global current_map_state
        
        try:
            # [Previous implementation remains the same until the end]
            print(f"\n=== MAP-AWARE PDOK TOOL ===")
            
            if location and not bbox:
                loc_data = find_location_coordinates(location)
                if "error" in loc_data:
                    return [{"error": loc_data["error"]}]
                
                lat, lon = loc_data["lat"], loc_data["lon"]
                
                if self.transformer_to_rd:
                    center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                    radius_m = radius_km * 1000
                    bbox = [center_x - radius_m, center_y - radius_m, center_x + radius_m, center_y + radius_m]
                    use_rd_coordinates = True
                else:
                    buffer = radius_km * 0.01
                    bbox = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]
                    use_rd_coordinates = False
                
                # Update map center
                current_map_state["center"] = [lon, lat]
            else:
                use_rd_coordinates = True if self.transformer_to_rd else False
            
            if not bbox:
                return [{"error": "Must provide either location or bbox parameter"}]
            
            # Build request (same as before)
            cql_filters = []
            if min_year:
                cql_filters.append(f"bouwjaar >= {min_year}")
            if max_year:
                cql_filters.append(f"bouwjaar <= {max_year}")
            cql_filter = " AND ".join(cql_filters) if cql_filters else None
            
            params = {
                'service': 'WFS', 'version': self.version, 'request': 'GetFeature',
                'typeName': self.typename, 'outputFormat': 'application/json',
                'count': max_features,
                'srsName': self.srs if use_rd_coordinates else 'EPSG:4326',
                'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{self.srs if use_rd_coordinates else 'EPSG:4326'}"
            }
            if cql_filter:
                params['cql_filter'] = cql_filter
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_features = data.get('features', [])
            
            if not raw_features:
                from MockBuildingTool import MockBuildingTool
                mock_tool = MockBuildingTool()
                result = mock_tool.forward(location or "Netherlands", max_features)
                # Update map state with mock data
                current_map_state["features"] = result
                current_map_state["last_updated"] = datetime.now().isoformat()
                return result
            
            # Process features (same logic as before)
            processed_features = []
            for i, feature in enumerate(raw_features):
                try:
                    props = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    if not geometry:
                        continue
                    
                    validated_geometry = validate_and_fix_geometry(geometry)
                    if not validated_geometry:
                        continue
                    
                    building_id = props.get('identificatie', f'Building_{i+1}')
                    building_year = props.get('bouwjaar', 'Unknown')
                    building_status = props.get('status', 'Unknown')
                    
                    # Calculate centroid and area
                    area_m2 = 0
                    avg_lon, avg_lat = 0, 0
                    
                    if validated_geometry['type'] == 'Polygon':
                        coords = validated_geometry['coordinates'][0]
                        if coords and len(coords) > 0:
                            avg_lon = sum(coord[0] for coord in coords) / len(coords)
                            avg_lat = sum(coord[1] for coord in coords) / len(coords)
                            
                            # Shoelace formula for area
                            n = len(coords)
                            area_m2 = 0.5 * abs(sum(coords[i][0] * coords[(i + 1) % n][1] - 
                                                   coords[(i + 1) % n][0] * coords[i][1] 
                                                   for i in range(n)))
                    elif validated_geometry['type'] == 'Point':
                        avg_lon, avg_lat = validated_geometry['coordinates']
                        area_m2 = 50
                    
                    # Convert to WGS84 if needed
                    if self.transformer_to_wgs84 and use_rd_coordinates and avg_lon != 0 and avg_lat != 0:
                        wgs84_coords = self.transformer_to_wgs84.transform(avg_lon, avg_lat)
                        avg_lon, avg_lat = wgs84_coords
                        
                        if validated_geometry['type'] == 'Polygon':
                            wgs84_coords_list = []
                            for coord in validated_geometry['coordinates'][0]:
                                wgs84_coord = self.transformer_to_wgs84.transform(coord[0], coord[1])
                                wgs84_coords_list.append([wgs84_coord[0], wgs84_coord[1]])
                            validated_geometry['coordinates'] = [wgs84_coords_list]
                    
                    if min_area and area_m2 < min_area:
                        continue
                    
                    building_name = f"Building {building_id[-6:]}" if len(building_id) > 6 else building_id
                    if building_year and building_year != 'Unknown':
                        building_name += f" ({building_year})"
                    
                    desc_parts = []
                    if building_year and building_year != 'Unknown':
                        desc_parts.append(f"Built: {building_year}")
                    if building_status and building_status != 'Unknown':
                        desc_parts.append(f"Status: {building_status}")
                    if area_m2 > 0:
                        desc_parts.append(f"Area: {area_m2:.0f}m²")
                    
                    num_units = props.get('aantal_verblijfsobjecten')
                    if num_units:
                        desc_parts.append(f"Units: {num_units}")
                    
                    description = " | ".join(desc_parts) if desc_parts else "Dutch building from PDOK database"
                    
                    enhanced_feature = {
                        "name": building_name,
                        "lat": float(avg_lat) if avg_lat != 0 else 0.0,
                        "lon": float(avg_lon) if avg_lon != 0 else 0.0,
                        "description": description,
                        "geometry": validated_geometry,
                        "properties": ensure_json_serializable({
                            **props,
                            "area_m2": area_m2,
                            "centroid_lat": float(avg_lat) if avg_lat != 0 else 0.0,
                            "centroid_lon": float(avg_lon) if avg_lon != 0 else 0.0,
                        })
                    }
                    
                    processed_features.append(enhanced_feature)
                    
                except Exception as feature_error:
                    print(f"Error processing feature {i}: {feature_error}")
                    continue
            
            if not processed_features:
                mock_tool = MockBuildingTool()
                result = mock_tool.forward(location or "Netherlands", max_features)
                current_map_state["features"] = result
                current_map_state["last_updated"] = datetime.now().isoformat()
                return result
            
            processed_features.sort(key=lambda x: x['properties'].get('area_m2', 0), reverse=True)
            
            # UPDATE MAP STATE
            current_map_state["features"] = processed_features
            current_map_state["last_updated"] = datetime.now().isoformat()
            
            if location:
                loc_coords = find_location_coordinates(location)
                if "error" not in loc_coords:
                    current_map_state["center"] = [loc_coords["lon"], loc_coords["lat"]]
                    current_map_state["zoom"] = 14
            
            print(f"Updated map state with {len(processed_features)} buildings")
            
            return processed_features
            
        except Exception as e:
            error_msg = f"PDOK tool error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]


class SimpleBuildingReturnTool(Tool):
    """Simple tool that returns building data directly for map display"""
    
    name = "return_buildings_for_map"
    description = "Return building data in the exact format needed for map display. Use this when the user asks to show, find, or display buildings."
    inputs = {
        "location": {
            "type": "string",
            "description": "Location to search for buildings (e.g., 'Amsterdam', 'Groningen')"
        },
        "count": {
            "type": "integer", 
            "description": "Number of buildings to find (default: 10)",
            "nullable": True
        }
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, location, count=10):
        """Get buildings and return them directly without any processing."""
        try:
            print(f"\n=== SIMPLE BUILDING RETURN TOOL ===")
            print(f"Location: {location}, Count: {count}")
            
            # Use the PDOK tool to get buildings
            pdok_tool = PDOKBuildingsAdvancedTool()
            buildings = pdok_tool.forward(
                location=location,
                max_features=count,
                min_area=50,  # Include smaller buildings
                radius_km=2.0
            )
            
            if not buildings or (len(buildings) > 0 and buildings[0].get('error')):
                print("PDOK failed, using mock data")
                mock_tool = MockBuildingTool()
                buildings = mock_tool.forward(location, count)
            
            if buildings and len(buildings) > 0:
                print(f"Returning {len(buildings)} buildings directly for map display")
                
                # Log first building for verification
                first_building = buildings[0]
                print(f"Sample building:")
                print(f"  Name: {first_building.get('name', 'Unknown')}")
                print(f"  Coordinates: {first_building.get('lat', 0)}, {first_building.get('lon', 0)}")
                print(f"  Has geometry: {'geometry' in first_building}")
                print(f"  Geometry type: {first_building.get('geometry', {}).get('type', 'None')}")
                
                return buildings
            else:
                return [{"error": "No buildings found"}]
                
        except Exception as e:
            error_msg = f"Simple building tool error: {str(e)}"
            print(error_msg)
            return [{"error": error_msg}]



# Enhanced Mock Building Tool
class MockBuildingTool(Tool):
    """Enhanced mock tool with map state updates"""
    
    name = "get_sample_buildings"
    description = "Get sample building data with proper geometry and update map state."
    inputs = {
        "location": {"type": "string", "description": "Location name"},
        "count": {"type": "integer", "description": "Number of buildings", "nullable": True}
    }
    output_type = "array"
    is_initialized = True
    
    def forward(self, location, count=5):
        """Generate sample buildings and update map state."""
        global current_map_state
        
        try:
            loc_data = find_location_coordinates(location)
            if "error" in loc_data:
                return [{"error": loc_data["error"]}]
            
            base_lat, base_lon = loc_data["lat"], loc_data["lon"]
            
            # Update map state
            current_map_state["center"] = [base_lon, base_lat]
            current_map_state["zoom"] = 15
            
            sample_buildings = [
                {
                    "name": "Historic Building 1851",
                    "lat": base_lat + 0.001,
                    "lon": base_lon + 0.002,
                    "description": "Built in 1851 | Status: In use | Area: 245m²",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [base_lon + 0.002, base_lat + 0.001], 
                            [base_lon + 0.0022, base_lat + 0.001], 
                            [base_lon + 0.0022, base_lat + 0.0012], 
                            [base_lon + 0.002, base_lat + 0.0012], 
                            [base_lon + 0.002, base_lat + 0.001]
                        ]]
                    },
                    "properties": ensure_json_serializable({
                        "bouwjaar": 1851, "status": "Pand in gebruik", "area_m2": 245,
                        "centroid_lat": base_lat + 0.001, "centroid_lon": base_lon + 0.002,
                        "identificatie": "MOCK100012062978"
                    })
                },
                # Add more buildings as before...
            ]
            
            buildings = sample_buildings[:count]
            
            # Update map state
            current_map_state["features"] = buildings
            current_map_state["last_updated"] = datetime.now().isoformat()
            
            return buildings
            
        except Exception as e:
            return [{"error": f"Mock tool error: {str(e)}"}]

# Initialize map-aware agent
agent = CodeAgent(
    model=model,
    tools=[
        find_location_coordinates,
        analyze_current_map_features,    # NEW: Map analysis tool
        get_map_context_info,           # NEW: Map context tool  
        answer_map_question,            # NEW: General map Q&A tool
        #PDOKBuildingsAdvancedTool(),
        SimpleBuildingReturnTool(),
        #MockBuildingTool(),
        DuckDuckGoSearchTool()
    ],
    max_steps=15,
    additional_authorized_imports=[
        "xml.etree.ElementTree", "json", "requests", "shapely.geometry", 
        "shapely.ops", "pyproj", "re", "statistics", "collections", "datetime"
    ]
)


def create_building_search_prompt(query_text, map_context):
    """Create a prompt that encourages direct building return."""
    return f"""
You are a map-aware AI assistant. The user is asking: "{query_text}"

Current map context: {map_context}

IMPORTANT INSTRUCTIONS:
- If the user is asking to show, find, display, or search for buildings, use return_buildings_for_map tool
- This tool returns building data in the exact format the frontend needs to display polygons on the map
- DO NOT process, summarize, or modify building data - return it directly
- For analysis questions about existing map content, use analyze_current_map_features
- For general GIS questions, use answer_map_question

The frontend needs raw building objects with:
- name, lat, lon coordinates
- geometry object with type and coordinates
- properties object with building details

User query: {query_text}
"""



# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries with improved building data interception and parameter extraction."""
    global current_map_state
    
    print("\n" + "="*60)
    print("RECEIVED MAP-AWARE QUERY REQUEST")
    print("="*60)
    
    data = request.json
    query_text = data.get('query', '')
    current_features = data.get('current_features', [])
    map_center = data.get('map_center', [5.2913, 52.1326])
    map_zoom = data.get('map_zoom', 8)
    
    print(f"Query text: {query_text}")
    print(f"Current features count: {len(current_features)}")
    
    # Update map state with frontend data
    if current_features:
        current_map_state["features"] = current_features
    current_map_state["center"] = map_center
    current_map_state["zoom"] = map_zoom
    
    # Check if this is a building search query
    is_building_query = any(keyword in query_text.lower() for keyword in [
        'building', 'show', 'find', 'display', 'search', 'get'
    ]) and any(location in query_text.lower() for location in [
        'amsterdam', 'rotterdam', 'utrecht', 'groningen', 'eindhoven', 
        'den haag', 'tilburg', 'haarlem', 'almere', 'breda', 'nijmegen'
    ])
    
    try:
        print("Running map-aware agent...")
        
        # ENHANCED BUILDING QUERY INTERCEPTION WITH PARAMETER EXTRACTION
        if is_building_query:
            print("🏢 Detected building query - intercepting for direct processing")
            
            # Extract location from query
            location = 'Amsterdam'  # default
            for loc in ['amsterdam', 'rotterdam', 'utrecht', 'groningen', 'eindhoven', 
                       'den haag', 'tilburg', 'haarlem', 'almere', 'breda', 'nijmegen']:
                if loc in query_text.lower():
                    location = loc.title()
                    break
            
            print(f"🎯 Extracted location: {location}")
            
            # EXTRACT PARAMETERS FROM QUERY
            import re
            
            # Extract number of buildings
            max_features = 10  # default
            number_matches = re.findall(r'\b(\d+)\s*buildings?', query_text.lower())
            if number_matches:
                max_features = min(int(number_matches[0]), 50)  # Cap at 50
                print(f"📊 Extracted max features: {max_features}")
            
            # Extract year range
            min_year = None
            max_year = None
            
            # Look for patterns like "between 2020 and 2024", "from 2020 to 2024", "built in 2020-2024"
            year_range_patterns = [
                r'between\s+(\d{4})\s+and\s+(\d{4})',
                r'from\s+(\d{4})\s+to\s+(\d{4})', 
                r'(\d{4})\s*-\s*(\d{4})',
                r'(\d{4})\s+to\s+(\d{4})',
                r'constructed\s+between\s+(\d{4})\s+and\s+(\d{4})'
            ]
            
            for pattern in year_range_patterns:
                matches = re.findall(pattern, query_text.lower())
                if matches:
                    min_year = int(matches[0][0])
                    max_year = int(matches[0][1])
                    print(f"📅 Extracted year range: {min_year} - {max_year}")
                    break
            
            # Look for single year mentions
            if not min_year and not max_year:
                year_patterns = [
                    r'built\s+in\s+(\d{4})',
                    r'from\s+(\d{4})',
                    r'since\s+(\d{4})',
                    r'after\s+(\d{4})',
                    r'before\s+(\d{4})'
                ]
                
                for pattern in year_patterns:
                    matches = re.findall(pattern, query_text.lower())
                    if matches:
                        year = int(matches[0])
                        if 'after' in pattern or 'since' in pattern:
                            min_year = year
                            print(f"📅 Extracted min year: {min_year}")
                        elif 'before' in pattern:
                            max_year = year
                            print(f"📅 Extracted max year: {max_year}")
                        else:
                            min_year = year
                            max_year = year
                            print(f"📅 Extracted specific year: {year}")
                        break
            
            # Extract area requirements
            min_area = None
            area_patterns = [
                r'larger?\s+than\s+(\d+)\s*m[²2]',
                r'bigger?\s+than\s+(\d+)\s*m[²2]',
                r'minimum\s+(\d+)\s*m[²2]',
                r'at\s+least\s+(\d+)\s*m[²2]'
            ]
            
            for pattern in area_patterns:
                matches = re.findall(pattern, query_text.lower())
                if matches:
                    min_area = int(matches[0])
                    print(f"📐 Extracted min area: {min_area}m²")
                    break
            
            # Look for building type keywords
            building_type_filters = []
            if any(word in query_text.lower() for word in ['historic', 'historical', 'old']):
                if not max_year:
                    max_year = 1950
                    print(f"🏛️  Historic buildings filter applied: max year {max_year}")
            elif any(word in query_text.lower() for word in ['modern', 'new', 'recent', 'contemporary']):
                if not min_year:
                    min_year = 2000
                    print(f"🏗️  Modern buildings filter applied: min year {min_year}")
            
            print(f"🔧 Final parameters: location={location}, max_features={max_features}, min_year={min_year}, max_year={max_year}, min_area={min_area}")
            
            # Get buildings directly with extracted parameters
            try:
                pdok_tool = PDOKBuildingsAdvancedTool()
                buildings = pdok_tool.forward(
                    location=location,
                    max_features=max_features,
                    min_year=min_year,      # NOW PASSING YEAR FILTERS
                    max_year=max_year,      # NOW PASSING YEAR FILTERS  
                    min_area=min_area or 50,  # Use extracted or default
                    radius_km=2.0
                )
                
                if not buildings or (len(buildings) > 0 and buildings[0].get('error')):
                    print("📍 PDOK failed, using mock data with parameters")
                    mock_tool = MockBuildingTool()
                    buildings = mock_tool.forward(location, max_features)
                
                if buildings and len(buildings) > 0 and not buildings[0].get('error'):
                    print(f"✅ Got {len(buildings)} buildings - sending directly to frontend")
                    
                    # Log building years for verification
                    years = [b.get('properties', {}).get('bouwjaar') for b in buildings]
                    years = [y for y in years if y and isinstance(y, (int, float))]
                    if years:
                        avg_year = sum(years) / len(years)
                        min_found = min(years)
                        max_found = max(years)
                        print(f"📊 Building years found: {min_found}-{max_found}, average: {avg_year:.0f}")
                        
                        # Check if we got the right year range
                        if min_year and max_year:
                            correct_years = [y for y in years if min_year <= y <= max_year]
                            print(f"🎯 Buildings in requested range ({min_year}-{max_year}): {len(correct_years)}/{len(years)}")
                    
                    # Validate and serialize buildings
                    valid_buildings = []
                    for building in buildings:
                        if (isinstance(building, dict) and 
                            building.get('lat', 0) != 0 and 
                            building.get('lon', 0) != 0 and
                            'geometry' in building):
                            
                            # Ensure JSON serialization
                            serialized_building = ensure_json_serializable(building)
                            
                            # Validate geometry
                            if 'geometry' in serialized_building:
                                validated_geom = validate_and_fix_geometry(serialized_building['geometry'])
                                if validated_geom:
                                    serialized_building['geometry'] = validated_geom
                                    valid_buildings.append(serialized_building)
                    
                    if valid_buildings:
                        print(f"🗺️  Returning {len(valid_buildings)} valid buildings for map display")
                        
                        # Update map state
                        current_map_state["features"] = valid_buildings
                        current_map_state["last_updated"] = datetime.now().isoformat()
                        
                        # Return building data directly - this will be plotted on map
                        return jsonify(valid_buildings)
                    
            except Exception as direct_error:
                print(f"❌ Direct building search failed: {direct_error}")
        
        # For non-building queries or when direct search fails, use the agent
        context_prompt = f"""
You are a map-aware AI assistant. The user is asking: "{query_text}"

Current map context:
- Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
- Zoom level: {map_zoom}
- Features on map: {len(current_features)}

For analysis questions about existing map content, use analyze_current_map_features.
For general GIS questions, use answer_map_question.
For other queries, provide helpful responses about mapping and geography.

User query: {query_text}
"""
        
        result = agent.run(context_prompt)
        
        print(f"\n--- AGENT RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # ENHANCED SECONDARY CHECK: Search for any building data in agent logs with deeper inspection
        building_data = None
        
        if hasattr(agent, 'logs') or hasattr(agent, 'memory'):
            print("🔍 Searching agent execution history for building data...")
            
            # Try both old logs and new memory.steps
            log_sources = []
            if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
                log_sources.append(('memory.steps', agent.memory.steps))
                print(f"   📚 Found memory.steps with {len(agent.memory.steps)} steps")
            if hasattr(agent, 'logs'):
                log_sources.append(('logs', agent.logs))
                print(f"   📚 Found logs with {len(agent.logs)} entries")
            
            for source_name, log_entries in log_sources:
                print(f"   🔍 Searching {source_name}...")
                
                for log_index, log_entry in enumerate(reversed(log_entries)):
                    print(f"      📋 Checking {source_name}[{len(log_entries)-1-log_index}]...")
                    
                    # Multiple ways to find tool calls
                    tool_calls_to_check = []
                    
                    # Method 1: Direct tool_calls attribute
                    if hasattr(log_entry, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.tool_calls)
                        print(f"         🔧 Found {len(log_entry.tool_calls)} direct tool calls")
                    
                    # Method 2: step_logs -> tool_calls
                    if hasattr(log_entry, 'step_logs'):
                        for step_log in log_entry.step_logs:
                            if hasattr(step_log, 'tool_calls'):
                                tool_calls_to_check.extend(step_log.tool_calls)
                        print(f"         🔧 Found step_logs with tool calls")
                    
                    # Method 3: action or tool_call attributes (for new memory structure)
                    if hasattr(log_entry, 'action') and hasattr(log_entry.action, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.action.tool_calls)
                        print(f"         🔧 Found action.tool_calls")
                    
                    # Method 4: Direct action.result (for new memory structure)
                    if hasattr(log_entry, 'action') and hasattr(log_entry.action, 'result'):
                        result = log_entry.action.result
                        if isinstance(result, list) and len(result) > 0:
                            first_item = result[0]
                            if (isinstance(first_item, dict) and
                                'geometry' in first_item and 'lat' in first_item and 
                                'lon' in first_item and 'name' in first_item and
                                first_item.get('lat', 0) != 0 and first_item.get('lon', 0) != 0):
                                
                                building_data = result
                                print(f"🏗️  ✅ Found building data in action.result: {len(building_data)} buildings")
                                break
                    
                    # Method 5: Check individual tool calls
                    for tool_call_index, tool_call in enumerate(tool_calls_to_check):
                        print(f"         🔧 Checking tool call {tool_call_index + 1}/{len(tool_calls_to_check)}")
                        
                        if hasattr(tool_call, 'result') and isinstance(tool_call.result, list):
                            if len(tool_call.result) > 0:
                                first_item = tool_call.result[0]
                                print(f"            📋 First result item type: {type(first_item)}")
                                
                                if (isinstance(first_item, dict) and
                                    'geometry' in first_item and 'lat' in first_item and 
                                    'lon' in first_item and 'name' in first_item and
                                    first_item.get('lat', 0) != 0 and first_item.get('lon', 0) != 0):
                                    
                                    building_data = tool_call.result
                                    print(f"🏗️  ✅ Found building data in tool call result: {len(building_data)} buildings")
                                    
                                    # Log sample building for verification
                                    sample = building_data[0]
                                    print(f"            📍 Sample: {sample['name']} at [{sample['lat']:.6f}, {sample['lon']:.6f}]")
                                    print(f"            🏗️  Geometry: {sample['geometry'].get('type', 'Unknown')}")
                                    print(f"            📅 Year: {sample.get('properties', {}).get('bouwjaar', 'Unknown')}")
                                    break
                                else:
                                    print(f"            ❌ Not building data (missing required fields)")
                    
                    if building_data:
                        break
                
                if building_data:
                    break
        
        # If we found building data in logs, return it for map display
        if building_data:
            print(f"🗺️  Processing {len(building_data)} buildings from agent logs")
            
            serialized_buildings = []
            for building in building_data:
                try:
                    if isinstance(building, dict):
                        serialized_building = ensure_json_serializable(building)
                        
                        if 'geometry' in serialized_building:
                            validated_geom = validate_and_fix_geometry(serialized_building['geometry'])
                            if validated_geom:
                                serialized_building['geometry'] = validated_geom
                                
                                lat = serialized_building.get('lat', 0)
                                lon = serialized_building.get('lon', 0)
                                
                                if lat != 0 and lon != 0:
                                    serialized_buildings.append(serialized_building)
                                    
                except Exception as e:
                    print(f"❌ Error processing building: {e}")
                    continue
            
            if serialized_buildings:
                print(f"✅ Returning {len(serialized_buildings)} buildings from logs for map display")
                
                current_map_state["features"] = serialized_buildings
                current_map_state["last_updated"] = datetime.now().isoformat()
                
                return jsonify(serialized_buildings)
        
        # Handle text responses (analysis, questions, etc.)
        response_content = None
        
        if hasattr(result, 'content'):
            response_content = result.content
        elif hasattr(result, 'text'):
            response_content = result.text
        elif isinstance(result, str):
            response_content = result
        elif isinstance(result, list):
            response_content = '\n'.join([str(item) for item in result])
        else:
            response_content = str(result)
        
        print(f"💬 Returning text response: {str(response_content)[:200]}...")
        return jsonify({"response": str(response_content)})
        
    except Exception as e:
        error_msg = f"Map-aware agent error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        print("="*60 + "\n")
        return jsonify({"error": error_msg})
        
        # For non-building queries or when direct search fails, use the agent
        context_prompt = f"""
You are a map-aware AI assistant. The user is asking: "{query_text}"

Current map context:
- Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
- Zoom level: {map_zoom}
- Features on map: {len(current_features)}

For analysis questions about existing map content, use analyze_current_map_features.
For general GIS questions, use answer_map_question.
For other queries, provide helpful responses about mapping and geography.

User query: {query_text}
"""
        
        result = agent.run(context_prompt)
        
        print(f"\n--- AGENT RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # SECONDARY CHECK: Search for any building data in agent logs (just in case)
        building_data = None
        
        if hasattr(agent, 'logs'):
            print("🔍 Searching agent logs for building data...")
            for log_entry in reversed(agent.logs):
                tool_calls_to_check = []
                
                if hasattr(log_entry, 'step_logs'):
                    for step_log in log_entry.step_logs:
                        if hasattr(step_log, 'tool_calls'):
                            tool_calls_to_check.extend(step_log.tool_calls)
                
                if hasattr(log_entry, 'tool_calls'):
                    tool_calls_to_check.extend(log_entry.tool_calls)
                
                for tool_call in tool_calls_to_check:
                    if (hasattr(tool_call, 'result') and 
                        isinstance(tool_call.result, list) and
                        len(tool_call.result) > 0):
                        
                        first_item = tool_call.result[0]
                        
                        if (isinstance(first_item, dict) and
                            'geometry' in first_item and
                            'lat' in first_item and
                            'lon' in first_item and
                            'name' in first_item and
                            first_item.get('lat', 0) != 0 and
                            first_item.get('lon', 0) != 0):
                            
                            building_data = tool_call.result
                            print(f"🏗️  Found building data in logs: {len(building_data)} buildings")
                            break
                
                if building_data:
                    break
        
        # If we found building data in logs, return it for map display
        if building_data:
            print(f"🗺️  Processing {len(building_data)} buildings from agent logs")
            
            serialized_buildings = []
            for building in building_data:
                try:
                    if isinstance(building, dict):
                        serialized_building = ensure_json_serializable(building)
                        
                        if 'geometry' in serialized_building:
                            validated_geom = validate_and_fix_geometry(serialized_building['geometry'])
                            if validated_geom:
                                serialized_building['geometry'] = validated_geom
                                
                                lat = serialized_building.get('lat', 0)
                                lon = serialized_building.get('lon', 0)
                                
                                if lat != 0 and lon != 0:
                                    serialized_buildings.append(serialized_building)
                                    
                except Exception as e:
                    print(f"❌ Error processing building: {e}")
                    continue
            
            if serialized_buildings:
                print(f"✅ Returning {len(serialized_buildings)} buildings from logs for map display")
                
                current_map_state["features"] = serialized_buildings
                current_map_state["last_updated"] = datetime.now().isoformat()
                
                return jsonify(serialized_buildings)
        
        # Handle text responses (analysis, questions, etc.)
        response_content = None
        
        if hasattr(result, 'content'):
            response_content = result.content
        elif hasattr(result, 'text'):
            response_content = result.text
        elif isinstance(result, str):
            response_content = result
        elif isinstance(result, list):
            response_content = '\n'.join([str(item) for item in result])
        else:
            response_content = str(result)
        
        print(f"💬 Returning text response: {str(response_content)[:200]}...")
        return jsonify({"response": str(response_content)})
        
    except Exception as e:
        error_msg = f"Map-aware agent error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        print("="*60 + "\n")
        return jsonify({"error": error_msg})


@app.route('/api/buildings', methods=['POST'])
def get_buildings_direct():
    """Direct building search endpoint that bypasses the agent."""
    try:
        data = request.json
        location = data.get('location', '')
        max_features = data.get('max_features', 10)
        
        if not location:
            return jsonify({"error": "Location is required"})
        
        print(f"Direct building search for: {location}")
        
        # Use PDOK tool directly
        pdok_tool = PDOKBuildingsAdvancedTool()
        buildings = pdok_tool.forward(
            location=location,
            max_features=max_features,
            min_area=50,  # Small minimum to get more results
            radius_km=2.0
        )
        
        if buildings and len(buildings) > 0 and not buildings[0].get('error'):
            print(f"Direct search found {len(buildings)} buildings")
            
            # Validate all buildings
            valid_buildings = []
            for building in buildings:
                if (isinstance(building, dict) and 
                    building.get('lat', 0) != 0 and 
                    building.get('lon', 0) != 0 and
                    'geometry' in building):
                    valid_buildings.append(building)
            
            if valid_buildings:
                print(f"Returning {len(valid_buildings)} valid buildings")
                return jsonify(valid_buildings)
        
        # Fallback to mock data
        print("Using mock data fallback")
        mock_tool = MockBuildingTool()
        mock_buildings = mock_tool.forward(location, max_features)
        return jsonify(mock_buildings)
            
    except Exception as e:
        error_msg = f"Direct building search error: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg})



@app.route('/api/map-state', methods=['GET'])
def get_map_state():
    """Get current map state for debugging."""
    global current_map_state
    return jsonify(current_map_state)

if __name__ == '__main__':
    print("Starting Map-Aware Flask server")
    print("New capabilities:")
    print("  - Map content analysis")
    print("  - Spatial pattern recognition") 
    print("  - GIS question answering")
    print("  - Context-aware responses")
    print("\nAvailable tools:")
    #for tool in agent.tools:
        #print(f"  - {tool.name}: {tool.description}")
    app.run(debug=True, port=5000)