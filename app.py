# app.py - FIXED AI Intent Detection with Correct Tool Loading

import os
import json
import yaml
import math
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool, Tool, DuckDuckGoSearchTool
import statistics
from collections import Counter
from datetime import datetime
import re

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

def load_system_prompt(file_path: str = "static/system_prompt.yml") -> dict:
    """Load system prompt from YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        print(f"✅ Successfully loaded system prompt from {file_path}")
        return config
    except FileNotFoundError:
        print(f"❌ System prompt file not found: {file_path}")
        print("Using default system prompt configuration")
        return {}
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML file {file_path}: {e}")
        print("Using default system prompt configuration")
        return {}
    except Exception as e:
        print(f"❌ Error loading system prompt from {file_path}: {e}")
        print("Using default system prompt configuration")
        return {}

@tool
def analyze_current_map_features() -> dict:
    """Analyzes the features currently displayed on the map and provides statistics and insights.
    
    Returns:
        Analysis of current map features including counts, statistics, and insights
    """
    try:
        global current_map_state
        features = current_map_state.get("features", [])
        
        if not features:
            return {
                "message": "No features are currently displayed on the map.",
                "feature_count": 0,
                "suggestions": ["Ask the AI to find buildings or addresses in a specific location"]
            }
        
        analysis = {
            "feature_count": len(features),
            "feature_types": {},
            "building_statistics": {},
            "geographic_info": {},
            "summary": ""
        }
        
        # Analyze feature types and properties
        geometry_types = []
        building_years = []
        building_areas = []
        locations = []
        
        for feature in features:
            if 'geometry' in feature and feature['geometry']:
                geom_type = feature['geometry'].get('type', 'Unknown')
                geometry_types.append(geom_type)
            
            props = feature.get('properties', {})
            
            # Building year analysis
            year = props.get('bouwjaar')
            if year and str(year).isdigit():
                building_years.append(int(year))
            
            # Area analysis  
            area = props.get('area_m2', 0) or props.get('oppervlakte_min', 0) or props.get('oppervlakte_max', 0)
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
                "average": round(statistics.mean(building_years))
            }
        
        if building_areas:
            analysis["building_statistics"]["area_stats"] = {
                "total_area_m2": round(sum(building_areas)),
                "average_area_m2": round(statistics.mean(building_areas)),
                "largest_building_m2": max(building_areas)
            }
        
        # Geographic analysis
        if locations:
            lats = [loc[0] for loc in locations]
            lons = [loc[1] for loc in locations]
            
            analysis["geographic_info"] = {
                "center_point": [round(statistics.mean(lats), 6), round(statistics.mean(lons), 6)],
                "spread_km": round(((max(lats) - min(lats)) * 111), 2)
            }
        
        # Generate summary
        summary_parts = [f"Currently displaying {len(features)} features on the map"]
        
        if building_years:
            year_stats = analysis["building_statistics"]["year_range"]
            summary_parts.append(f"Buildings from {year_stats['oldest']} to {year_stats['newest']}")
        
        if building_areas:
            area_stats = analysis["building_statistics"]["area_stats"]
            summary_parts.append(f"Total area: {area_stats['total_area_m2']:,}m²")
        
        analysis["summary"] = ". ".join(summary_parts) + "."
        
        # Update global state
        current_map_state["statistics"] = analysis
        current_map_state["last_updated"] = datetime.now().isoformat()
        
        return analysis
        
    except Exception as e:
        return {"error": f"Error analyzing map features: {str(e)}"}

@tool  
def get_map_context_info() -> dict:
    """Provides information about the current map view, center, and context.
    
    Returns:
        Current map context including center point, zoom level, and view area
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
    """Answers general questions about maps, geography, GIS, and spatial analysis.
    
    Args:
        question: The map-related question to answer
        
    Returns:
        Answer to the map question
    """
    try:
        question_lower = question.lower()
        
        # Map concepts and definitions
        if any(term in question_lower for term in ['what is gis', 'geographic information system']):
            return """GIS (Geographic Information System) is a framework for gathering, managing, and analyzing spatial and geographic data. It combines hardware, software, and data to capture, manage, analyze, and display all forms of geographically referenced information."""
        
        elif any(term in question_lower for term in ['what is wgs84', 'coordinate system']):
            return """WGS84 (World Geodetic System 1984) is the standard coordinate system used by GPS and most web mapping applications. It defines locations using latitude and longitude in decimal degrees. In the Netherlands, we also use RD New (EPSG:28992), which is the national coordinate system optimized for accurate measurements within Dutch borders."""
        
        elif any(term in question_lower for term in ['what is pdok', 'pdok']):
            return """PDOK (Publieke Dienstverlening Op de Kaart) is the Dutch national spatial data infrastructure. It provides free access to geographic datasets from Dutch government organizations, including building data (BAG), topographic maps, aerial imagery, and administrative boundaries. It's the authoritative source for Dutch geographic information."""
        
        elif any(term in question_lower for term in ['what is bag', 'buildings and addresses']):
            return """BAG (Basisregistratie Adressen en Gebouwen) is the Dutch Buildings and Addresses Database. It contains authoritative information about all buildings, addresses, and premises in the Netherlands. Each building has a unique identifier and includes details like construction year, status, area, and precise polygon geometry."""
        
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

def create_agent_with_ai_intelligence():
    """FIXED: Create the map-aware agent with correct tool loading including coordinate conversion."""
    
    print("🔧 FIXED: Loading PDOK intelligent tools with coordinate conversion...")
    
    # Try multiple import strategies to find working tools
    intelligent_tools = []
    tools_available = False
    
    # Always include coordinate conversion tools
    coordinate_tools = []
    try:
        from tools.coordinate_conversion_tool import CoordinateConversionTool, CreateRDBoundingBoxTool
        coordinate_tools = [
            CoordinateConversionTool(),
            CreateRDBoundingBoxTool()
        ]
        print("✅ Successfully loaded coordinate conversion tools")
    except ImportError as e:
        print(f"⚠️ Could not import coordinate tools: {e}")
        print("🔧 Creating coordinate tools inline...")
        
        # Create coordinate conversion tools inline if import fails
        @tool
        def convert_coordinates_to_rd_new(latitude: float, longitude: float) -> dict:
            """Convert WGS84 coordinates to RD New coordinates for PDOK requests."""
            import math
            
            try:
                print(f"🔄 Converting WGS84 ({longitude:.6f}, {latitude:.6f}) to RD New...")
                
                # Validate input
                if not (50.5 <= latitude <= 54.0 and 3.0 <= longitude <= 7.5):
                    return {"error": f"Coordinates outside Netherlands bounds"}
                
                # Convert to radians
                lat_rad = math.radians(latitude)
                lon_rad = math.radians(longitude)
                
                # RD New reference point (Amersfoort)
                lat0 = math.radians(52.15616055555555)
                lon0 = math.radians(5.38763888888889)
                
                # Simplified but accurate transformation
                x0, y0 = 155000.0, 463000.0
                k = 0.9999079
                
                # Calculate differences
                dlat = lat_rad - lat0
                dlon = lon_rad - lon0
                
                # Transformation (simplified)
                x = x0 + k * 6382644.571 * dlon * math.cos(lat0) + \
                    k * 6382644.571 * dlat * dlon * math.sin(lat0) / 2
                y = y0 + k * 6382644.571 * dlat + \
                    k * 6382644.571 * dlon * dlon * math.cos(lat0) * math.sin(lat0) / 2
                
                print(f"✅ RD New coordinates: X={x:.2f}, Y={y:.2f}")
                
                # Create 1km bounding box
                radius_m = 1000
                bbox = f"{x-radius_m},{y-radius_m},{x+radius_m},{y+radius_m}"
                
                return {
                    "rd_x": x,
                    "rd_y": y,
                    "bbox_rd_1km": bbox,
                    "coordinate_system": "EPSG:28992"
                }
                
            except Exception as e:
                return {"error": f"Coordinate conversion failed: {str(e)}"}
        
        @tool
        def create_rd_bounding_box(rd_x: float, rd_y: float, radius_km: float = 1.0) -> dict:
            """Create RD New bounding box for PDOK requests."""
            try:
                radius_m = radius_km * 1000
                bbox = f"{rd_x-radius_m},{rd_y-radius_m},{rd_x+radius_m},{rd_y+radius_m}"
                print(f"📦 Created RD bbox: {bbox}")
                return {
                    "bbox": bbox,
                    "radius_km": radius_km,
                    "coordinate_system": "EPSG:28992"
                }
            except Exception as e:
                return {"error": f"Bbox creation failed: {str(e)}"}
        
        coordinate_tools = [convert_coordinates_to_rd_new, create_rd_bounding_box]
        print("✅ Created inline coordinate conversion tools")
    
    # Strategy 1: Try enhanced tools
    try:
        from tools.enhanced_ai_intelligent_tools import (
            EnhancedPDOKServiceDiscoveryTool,
            LocationSearchTool,
            PDOKDataRequestTool
        )
        
        intelligent_tools = [
            EnhancedPDOKServiceDiscoveryTool(),
            LocationSearchTool(),
            PDOKDataRequestTool(),
        ]
        print("✅ Successfully loaded ENHANCED intelligent tools")
        tools_available = True
        
    except ImportError as e1:
        print(f"⚠️ Could not import enhanced tools: {e1}")
        
        # Strategy 2: Try original tools
        try:
            from tools.ai_intelligent_tools import (
                PDOKServiceDiscoveryTool,
                LocationSearchTool,
                PDOKDataRequestTool
            )
            
            intelligent_tools = [
                PDOKServiceDiscoveryTool(),
                LocationSearchTool(),
                PDOKDataRequestTool(),
            ]
            print("✅ Successfully loaded ORIGINAL intelligent tools")
            tools_available = True
            
        except ImportError as e2:
            print(f"⚠️ Could not import original tools: {e2}")
            
            # Strategy 3: Try modular tools
            try:
                from tools.pdok_modular_tools import (
                    PDOKLocationSearchTool,
                    PDOKBuildingSearchTool
                )
                
                intelligent_tools = [
                    PDOKLocationSearchTool(),
                    PDOKBuildingSearchTool(),
                ]
                print("✅ Successfully loaded MODULAR tools")
                tools_available = True
                
            except ImportError as e3:
                print(f"⚠️ Could not import modular tools: {e3}")
                
                # Strategy 4: Try service discovery tools
                try:
                    from tools.pdok_service_discovery_tool import (
                        PDOKServiceDiscoveryTool,
                        PDOKDataRequestTool
                    )
                    
                    intelligent_tools = [
                        PDOKServiceDiscoveryTool(),
                        PDOKDataRequestTool(),
                    ]
                    print("✅ Successfully loaded SERVICE DISCOVERY tools")
                    tools_available = True
                    
                except ImportError as e4:
                    print(f"❌ Could not import any PDOK tools: {e4}")
                    print("🔄 Will use basic tools only")
                    tools_available = False
    
    # Combine all available tools
    tools = []
    tools.extend(coordinate_tools)  # ALWAYS include coordinate conversion
    tools.extend(intelligent_tools)
    
    # Add built-in tools that should always work
    tools.extend([
        analyze_current_map_features,
        get_map_context_info,
        answer_map_question,
        DuckDuckGoSearchTool()
    ])

    print(f"🧠 FIXED: Creating AI agent with {len(tools)} tools (including coordinate conversion):")
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = str(type(tool).__name__)
        print(f"  ✅ {tool_name}")
    
    # Load system prompt
    system_prompt_config = load_system_prompt("static/system_prompt.yml")
    
    # Create agent with proper tool registration
    if system_prompt_config:
        print("✅ Using FIXED system prompt configuration with coordinate conversion")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=20,
            prompt_templates=system_prompt_config,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "shapely.geometry", 
                "shapely.ops", "pyproj", "re", "statistics", "collections", "datetime", "math"
            ]
        )
    else:
        print("⚠️ Using default system prompt")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=20,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "shapely.geometry", 
                "shapely.ops", "pyproj", "re", "statistics", "collections", "datetime", "math"
            ]
        )
    
    # CRITICAL: Verify tools are properly registered
    print("\n🔍 FIXED: Verifying tool registration...")
    if hasattr(agent, 'tools'):
        print(f"✅ Agent has {len(agent.tools)} registered tools:")
        for tool_name, tool_obj in agent.tools.items():
            print(f"   - {tool_name}: {type(tool_obj).__name__}")
    else:
        print("⚠️ Could not verify tool registration")
    
    return agent, tools_available

# Initialize the agent with correct tool loading
agent, tools_available = create_agent_with_ai_intelligence()

# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('base.html')

def extract_search_coordinates_from_agent_logs(agent):
    """FIXED: Extract search coordinates from agent execution logs with enhanced pattern matching."""
    try:
        print("🔍 FIXED: Enhanced extraction of search coordinates from agent memory...")
        
        if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
            for step in agent.memory.steps:
                # Check observation text for location coordinates
                if hasattr(step, 'observation') and step.observation:
                    observation_text = str(step.observation)
                    
                    # ENHANCED: Look for the specific pattern from the logs
                    # Pattern: "Location data obtained: {'name': 'Leonard Springerlaan 37, 2033TB Haarlem', 'lat': 52.37539091, 'lon': 4.65928468, ...}"
                    location_data_match = re.search(r"Location data obtained: (\{[^}]+\})", observation_text)
                    if location_data_match:
                        try:
                            # Extract and parse the dictionary
                            location_dict_str = location_data_match.group(1)
                            # Use eval safely since this is our own tool output
                            location_data = eval(location_dict_str)
                            
                            if (isinstance(location_data, dict) and 
                                'lat' in location_data and 'lon' in location_data and
                                'name' in location_data):
                                
                                lat = float(location_data['lat'])
                                lon = float(location_data['lon'])
                                name = location_data['name']
                                
                                print(f"✅ FOUND SEARCH LOCATION from agent observation: {name} at {lat}, {lon}")
                                return {
                                    "lat": lat,
                                    "lon": lon,
                                    "name": name,
                                    "source": "agent_observation_enhanced"
                                }
                        except Exception as e:
                            print(f"⚠️ Error parsing location data: {e}")
                    
                    # ENHANCED: Look for explicit coordinate output patterns
                    # Pattern: "Location found: [name] at [lat], [lon]"
                    location_found_match = re.search(r"Location found: (.+?) at (\d+\.\d+), (\d+\.\d+)", observation_text)
                    if location_found_match:
                        name = location_found_match.group(1)
                        lat = float(location_found_match.group(2))
                        lon = float(location_found_match.group(3))
                        
                        print(f"✅ FOUND SEARCH LOCATION from 'Location found' pattern: {name} at {lat}, {lon}")
                        return {
                            "lat": lat,
                            "lon": lon,
                            "name": name,
                            "source": "agent_location_found_pattern"
                        }
                    
                    # ENHANCED: Look for coordinate pairs in observation
                    # Pattern: coordinates like "52.37539091, 4.65928468"
                    coord_pairs = re.findall(r"(\d{2}\.\d{8}),?\s*(\d\.\d{8})", observation_text)
                    if coord_pairs:
                        lat, lon = float(coord_pairs[0][0]), float(coord_pairs[0][1])
                        # Validate coordinates are in Netherlands bounds
                        if 50.5 <= lat <= 54.0 and 3.0 <= lon <= 7.5:
                            # Try to find associated name
                            name_match = re.search(r"'name':\s*'([^']+)'", observation_text)
                            name = name_match.group(1) if name_match else f"Location at {lat}, {lon}"
                            
                            print(f"✅ FOUND SEARCH LOCATION from coordinate pair: {name} at {lat}, {lon}")
                            return {
                                "lat": lat,
                                "lon": lon,
                                "name": name,
                                "source": "agent_coordinate_pair"
                            }
                    
                    # Look for JSON-like structures with location data
                    try:
                        json_matches = re.findall(r'\{[^{}]*"lat"[^{}]*\}', observation_text)
                        for json_str in json_matches:
                            try:
                                location_data = json.loads(json_str.replace("'", '"'))
                                if (isinstance(location_data, dict) and 
                                    'lat' in location_data and 'lon' in location_data and
                                    not location_data.get('error')):
                                    
                                    lat = float(location_data['lat'])
                                    lon = float(location_data['lon'])
                                    name = location_data.get('name', f"Location at {lat}, {lon}")
                                    
                                    # Validate coordinates
                                    if 50.5 <= lat <= 54.0 and 3.0 <= lon <= 7.5:
                                        print(f"✅ FOUND SEARCH LOCATION from JSON: {name} at {lat}, {lon}")
                                        return {
                                            "lat": lat,
                                            "lon": lon,
                                            "name": name,
                                            "source": "agent_json_enhanced"
                                        }
                            except (json.JSONDecodeError, ValueError, KeyError):
                                continue
                    except Exception:
                        pass
                
                # Check tool calls for search_location_coordinates specifically
                if hasattr(step, 'tool_calls'):
                    for tool_call in step.tool_calls:
                        tool_name = getattr(tool_call, 'tool_name', 'unknown')
                        
                        # ONLY look at search_location_coordinates tool calls
                        if tool_name == 'search_location_coordinates' and hasattr(tool_call, 'result'):
                            location_result = tool_call.result
                            
                            if (isinstance(location_result, dict) and 
                                not location_result.get('error') and
                                'lat' in location_result and 'lon' in location_result):
                                
                                lat = float(location_result['lat'])
                                lon = float(location_result['lon'])
                                name = location_result.get('name', 'Search Location')
                                
                                # Validate coordinates
                                if 50.5 <= lat <= 54.0 and 3.0 <= lon <= 7.5:
                                    print(f"✅ FOUND SEARCH LOCATION from tool call: {name} at {lat}, {lon}")
                                    return {
                                        "lat": lat,
                                        "lon": lon,
                                        "name": name,
                                        "source": "tool_call_enhanced"
                                    }
                                else:
                                    print(f"❌ Invalid coordinates from tool call: {lat}, {lon}")
        
        print("⚠️ No search location found in agent memory")
        return None
        
    except Exception as e:
        print(f"❌ Error extracting search coordinates: {e}")
        return None

def extract_and_parse_json_response(result_text):
    """FIXED: Complete JSON extraction that handles truncated responses."""
    try:
        print("🔍 COMPLETE FIX: Enhanced JSON parsing from AI response...")
        print(f"📝 Response text length: {len(result_text)}")
        
        # Method 1: Look for complete final_answer JSON in the last part of the response
        final_answer_patterns = [
            r'final_answer\(json\.dumps\(([^)]+)\)\)',  # final_answer(json.dumps(...))
            r'final_answer\(([^)]+)\)',                 # final_answer(...)
            r'Out - Final answer:\s*(.+?)(?:\n|$)',     # Out - Final answer: ...
        ]
        
        for pattern in final_answer_patterns:
            matches = re.findall(pattern, result_text, re.DOTALL)
            for match in matches:
                try:
                    print(f"🎯 Testing pattern match: {match[:100]}...")
                    
                    # Clean the match
                    cleaned = match.strip()
                    
                    # Handle different quote styles and escaping
                    if cleaned.startswith('"') and cleaned.endswith('"'):
                        cleaned = cleaned[1:-1]
                    elif cleaned.startswith("'") and cleaned.endswith("'"):
                        cleaned = cleaned[1:-1]
                    
                    # Unescape if needed
                    if '\\u' in cleaned or '\\"' in cleaned:
                        import codecs
                        try:
                            cleaned = codecs.decode(cleaned, 'unicode_escape')
                        except:
                            # Try manual unescaping
                            cleaned = cleaned.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                    
                    # Try to parse
                    if cleaned.strip().startswith('{') and 'geojson_data' in cleaned:
                        parsed = json.loads(cleaned)
                        if (isinstance(parsed, dict) and 
                            'text_description' in parsed and 
                            'geojson_data' in parsed):
                            print("✅ COMPLETE FIX: Found valid JSON response!")
                            return parsed, True
                            
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"⚠️ Parse error: {e}")
                    continue
        
        # Method 2: Reconstruct from truncated response
        if '"text_description":' in result_text and '"geojson_data":' in result_text:
            print("🔧 COMPLETE FIX: Attempting to reconstruct truncated JSON...")
            
            try:
                # Extract text description
                text_desc_pattern = r'"text_description":\s*"([^"]*)"'
                text_match = re.search(text_desc_pattern, result_text)
                text_description = text_match.group(1) if text_match else "Buildings found"
                
                # Find the geojson_data section
                geojson_start = result_text.find('"geojson_data": [')
                if geojson_start != -1:
                    # Extract everything after geojson_data start
                    geojson_section = result_text[geojson_start + 16:]  # Skip '"geojson_data": ['
                    
                    # Find individual feature objects
                    features = []
                    brace_count = 0
                    current_feature = ""
                    in_string = False
                    escape_next = False
                    
                    for char in geojson_section:
                        if escape_next:
                            current_feature += char
                            escape_next = False
                            continue
                            
                        if char == '\\':
                            escape_next = True
                            current_feature += char
                            continue
                            
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            
                        if not in_string:
                            if char == '{':
                                if brace_count == 0:
                                    current_feature = "{"
                                else:
                                    current_feature += char
                                brace_count += 1
                            elif char == '}':
                                current_feature += char
                                brace_count -= 1
                                if brace_count == 0:
                                    # Complete feature found
                                    try:
                                        feature = json.loads(current_feature)
                                        if (isinstance(feature, dict) and 
                                            'name' in feature and 'lat' in feature and 'lon' in feature):
                                            features.append(feature)
                                    except json.JSONDecodeError:
                                        pass
                                    current_feature = ""
                            elif brace_count > 0:
                                current_feature += char
                        else:
                            if brace_count > 0:
                                current_feature += char
                    
                    if features:
                        reconstructed = {
                            "text_description": text_description,
                            "geojson_data": features
                        }
                        print(f"✅ COMPLETE FIX: Reconstructed JSON with {len(features)} features!")
                        return reconstructed, True
                        
            except Exception as e:
                print(f"⚠️ Reconstruction error: {e}")
        
        # Method 3: Extract from agent memory if available
        print("🔍 COMPLETE FIX: Checking for response in context...")
        
        # Look for any JSON-like structures
        json_pattern = r'\{[^{}]*"text_description"[^{}]*\}'
        json_matches = re.findall(json_pattern, result_text, re.DOTALL)
        
        for json_str in json_matches:
            try:
                parsed = json.loads(json_str)
                if (isinstance(parsed, dict) and 
                    'text_description' in parsed):
                    # Add empty geojson_data if missing
                    if 'geojson_data' not in parsed:
                        parsed['geojson_data'] = []
                    print("✅ COMPLETE FIX: Found basic JSON structure!")
                    return parsed, True
            except json.JSONDecodeError:
                continue
        
        print("❌ COMPLETE FIX: No valid JSON found - response may be incomplete")
        return None, False
        
    except Exception as e:
        print(f"❌ COMPLETE FIX: Error in JSON parsing: {e}")
        return None, False




def process_agent_result_completely(agent_result, agent):
    """Process agent result with better handling of long responses."""
    try:
        print("🔄 COMPLETE FIX: Processing agent result...")
        
        # Get the complete result text
        if hasattr(agent_result, 'content'):
            result_text = agent_result.content
        elif hasattr(agent_result, 'text'):  
            result_text = agent_result.text
        elif isinstance(agent_result, str):
            result_text = agent_result
        else:
            result_text = str(agent_result)
        
        print(f"📊 Result length: {len(result_text)} characters")
        
        # Check if response appears truncated
        is_truncated = (
            result_text.endswith('...') or 
            result_text.count('{') != result_text.count('}') or
            ('"geojson_data":' in result_text and not result_text.strip().endswith('}')) or
            ('final_answer(' in result_text and result_text.count('final_answer(') > result_text.count(')'))
        )
        
        if is_truncated:
            print("⚠️ COMPLETE FIX: Response appears truncated - attempting recovery...")
            
            # Try to get complete response from agent memory
            if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
                longest_text = result_text
                
                for step in reversed(agent.memory.steps):  # Check latest steps first
                    if hasattr(step, 'observation') and step.observation:
                        obs_text = str(step.observation)
                        
                        # Look for final_answer in observations
                        if 'final_answer(' in obs_text and len(obs_text) > len(longest_text):
                            print("✅ COMPLETE FIX: Found longer response in agent memory!")
                            longest_text = obs_text
                        
                        # Also check for JSON content
                        elif '"geojson_data":' in obs_text and len(obs_text) > len(longest_text):
                            print("✅ COMPLETE FIX: Found JSON content in agent memory!")
                            longest_text = obs_text
                
                if len(longest_text) > len(result_text):
                    print(f"🔄 Using longer text: {len(longest_text)} vs {len(result_text)} chars")
                    result_text = longest_text
        
        return result_text
        
    except Exception as e:
        print(f"❌ Error processing agent result: {e}")
        return str(agent_result)
        
@app.route('/api/query', methods=['POST'])
def query():
    """FIXED: Handle chat queries with improved JSON response parsing."""
    global current_map_state
    
    print("\n" + "="*80)
    print("🧠 FIXED AI INTELLIGENCE - IMPROVED JSON PARSING")
    print("="*80)
    
    data = request.json
    query_text = data.get('query', '')
    current_features = data.get('current_features', [])
    map_center = data.get('map_center', [5.2913, 52.1326])
    map_zoom = data.get('map_zoom', 8)
    
    print(f"Query text: {query_text}")
    print(f"Current features count: {len(current_features)}")
    print(f"Map context: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E (zoom: {map_zoom})")
    
    # Update map state
    if current_features:
        current_map_state["features"] = current_features
    current_map_state["center"] = map_center
    current_map_state["zoom"] = map_zoom
    
    try:
        print("🧠 Running FIXED AI with improved JSON parsing...")
        
        # Enhanced context prompt with better JSON formatting instructions
        context_prompt = f"""
        User query: "{query_text}"

        Current map context:
        - Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
        - Zoom level: {map_zoom}
        - Features on map: {len(current_features)}

        CRITICAL RESPONSE FORMAT INSTRUCTIONS:
        
        When you find geographic data (buildings, addresses, etc.), you MUST format your response as:
        
        ```python
        import json
        
        response = {{
            "text_description": "Your detailed description here",
            "geojson_data": [
                {{
                    "name": "Feature Name",
                    "lat": 52.123456,
                    "lon": 6.123456,
                    "description": "Feature description", 
                    "geometry": {{"type": "Point/Polygon", "coordinates": [...]}},
                    "properties": {{"key": "value", ...}}
                }}
                // ... more features
            ]
        }}
        
        final_answer(json.dumps(response))
        ```
        
        CRITICAL JSON FORMATTING RULES:
        1. Always use json.dumps() in final_answer()
        2. Ensure valid JSON syntax - no trailing commas
        3. Include ALL features in geojson_data array
        4. Make sure coordinates are valid numbers
        5. Include proper geometry objects for map display
        
        WORKFLOW:
        1. Find location coordinates
        2. Search for buildings/data
        3. Process ALL results into proper JSON format
        4. Use final_answer(json.dumps(response))
        
        Now analyze the user's request and provide a properly formatted JSON response.
        """
        
        result = agent.run(context_prompt)
        
        print(f"\n--- FIXED AI RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # Process AI result
        if hasattr(result, 'content'):
            result_text = result.content
        elif hasattr(result, 'text'):  
            result_text = result.text
        elif isinstance(result, str):
            result_text = result
        else:
            result_text = str(result)
        
        print(f"Result text length: {len(result_text)}")
        print(f"Contains 'final_answer': {'final_answer' in result_text}")
        print(f"Contains 'geojson_data': {'geojson_data' in result_text}")
        
        # Extract search coordinates
        search_location = extract_search_coordinates_from_agent_logs(agent)
        if search_location:
            print(f"📍 EXTRACTED SEARCH LOCATION: {search_location['name']} at {search_location['lat']}, {search_location['lon']}")
        
        # FIXED: Enhanced JSON detection and parsing
        parsed_response, found_json = extract_and_parse_json_response(result_text)
        
        if found_json and parsed_response:
            print("✅ SUCCESSFULLY PARSED structured JSON response")
            
            text_description = parsed_response.get('text_description', '')
            geojson_data = parsed_response.get('geojson_data', [])
            
            print(f"📝 Text description: {text_description[:100]}...")
            print(f"🗺️ GeoJSON features: {len(geojson_data)}")
            
            # Validate and process geographic data
            if isinstance(geojson_data, list) and len(geojson_data) > 0:
                processed_features = []
                
                for i, feature in enumerate(geojson_data):
                    try:
                        if isinstance(feature, dict) and 'lat' in feature and 'lon' in feature:
                            lat = float(feature['lat'])
                            lon = float(feature['lon'])
                            
                            if lat != 0 and lon != 0 and not (math.isnan(lat) or math.isnan(lon)):
                                # Validate and fix geometry
                                if 'geometry' in feature:
                                    validated_geom = validate_and_fix_geometry(feature['geometry'])
                                    if validated_geom:
                                        feature['geometry'] = validated_geom
                                    else:
                                        # Create point geometry if validation fails
                                        feature['geometry'] = {
                                            'type': 'Point',
                                            'coordinates': [lon, lat]
                                        }
                                else:
                                    # Add point geometry if missing
                                    feature['geometry'] = {
                                        'type': 'Point', 
                                        'coordinates': [lon, lat]
                                    }
                                
                                # Ensure properties are serializable
                                if 'properties' in feature:
                                    feature['properties'] = ensure_json_serializable(feature['properties'])
                                else:
                                    feature['properties'] = {}
                                
                                # Ensure required fields
                                feature['lat'] = lat
                                feature['lon'] = lon
                                if 'name' not in feature:
                                    feature['name'] = f"Feature {i+1}"
                                if 'description' not in feature:
                                    feature['description'] = "PDOK Feature"
                                
                                processed_features.append(feature)
                                
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"⚠️ Error processing feature {i+1}: {e}")
                        continue
                
                if processed_features:
                    print(f"🎉 SUCCESSFULLY PROCESSED {len(processed_features)} valid features!")
                    
                    # Update global map state
                    current_map_state["features"] = processed_features
                    current_map_state["last_updated"] = datetime.now().isoformat()
                    
                    # Create response with geographic data
                    response_data = {
                        "response": text_description,
                        "geojson_data": processed_features,
                        "agent_type": "ai_intelligent_geographic",
                        "ai_method": "intelligent_analysis_fixed_json",
                        "features_processed": len(processed_features),
                        "original_features": len(geojson_data)
                    }
                    
                    # Include search location if found
                    if search_location:
                        response_data["search_location"] = search_location
                        print(f"📍 Including search location: {search_location['name']}")
                    
                    print("🎉 RETURNING STRUCTURED RESPONSE WITH VALID GEOJSON DATA!")
                    return jsonify(response_data)
                
                else:
                    print("❌ No valid features after processing - all features were invalid")
                    error_msg = f"Found {len(geojson_data)} features but none were valid for map display"
                    
            else:
                print("❌ No geojson_data array found or empty")
                error_msg = "Response contained no geographic data to display"
            
            # Text-only response
            response_data = {
                "response": text_description if text_description else str(result_text),
                "agent_type": "ai_intelligent_text",
                "ai_method": "intelligent_analysis_text_only",
                "issue": error_msg if 'error_msg' in locals() else "No geographic data"
            }
            
            if search_location:
                response_data["search_location"] = search_location
            
            return jsonify(response_data)
        
        else:
            print("❌ FAILED to parse JSON from AI response")
            print("🔍 Response preview:", result_text[:500])
            
            # Try to extract any useful information
            response_data = {
                "response": str(result_text),
                "agent_type": "ai_text_fallback", 
                "ai_method": "json_parsing_failed",
                "debug_info": {
                    "contains_final_answer": "final_answer" in result_text,
                    "contains_geojson": "geojson_data" in result_text,
                    "response_length": len(result_text)
                }
            }
            
            if search_location:
                response_data["search_location"] = search_location
            
            return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"AI processing error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        
        # Try to extract search location even on error
        search_location = None
        try:
            search_location = extract_search_coordinates_from_agent_logs(agent)
        except:
            pass
        
        error_response = {
            "error": error_msg,
            "agent_type": "error",
            "ai_method": "exception_occurred"
        }
        
        if search_location:
            error_response["search_location"] = search_location
        
        return jsonify(error_response)

    finally:
        print("🏁 FIXED JSON PARSING QUERY COMPLETED")
        print("="*80 + "\n")

@app.route('/api/map-state', methods=['GET'])
def get_map_state():
    """Get current map state for debugging."""
    global current_map_state
    return jsonify(current_map_state)

@app.route('/api/reload-prompt', methods=['POST'])
def reload_system_prompt():
    """Reload the system prompt and recreate the agent."""
    global agent, tools_available
    try:
        print("🔄 Reloading system prompt...")
        agent, tools_available = create_agent_with_ai_intelligence()
        return jsonify({
            "success": True,
            "message": "System prompt reloaded successfully with FIXED tool loading"
        })
    except Exception as e:
        error_msg = f"Error reloading system prompt: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        })

@app.route('/api/test-ai-intelligence', methods=['POST'])
def test_ai_intelligence():
    """Test endpoint for AI intelligence approach."""
    data = request.json
    test_query = data.get('query', 'Show me buildings near Amsterdam')
    
    try:
        print(f"🧪 Testing FIXED AI intelligence with: '{test_query}'")
        
        # Check available tools
        available_tools = []
        if hasattr(agent, 'tools'):
            available_tools = list(agent.tools.keys())
        
        return jsonify({
            "success": True,
            "query": test_query,
            "message": "FIXED AI intelligence system is ready to analyze this query",
            "ai_approach": "The AI will check available tools and adapt its approach accordingly",
            "tools_available": tools_available,
            "available_tools": available_tools,
            "fixes_applied": [
                "Multiple tool import strategies with fallbacks",
                "Tool availability verification before execution", 
                "Adaptive workflow based on available tools",
                "Enhanced error handling for missing tools",
                "Web search fallbacks when PDOK tools unavailable"
            ]
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    print("🚀 Starting FIXED AI-INTELLIGENT Map-Aware Flask server")
    print("="*80)
    print("🧠 FIXED AI INTELLIGENCE ARCHITECTURE:")
    print("  ✅ Multiple tool import strategies with fallbacks")
    print("  ✅ Tool availability verification before execution")
    print("  ✅ Adaptive AI workflow based on available tools")
    print("  ✅ Web search fallbacks for missing PDOK tools")
    print("  ✅ Enhanced error handling and debugging")
    print("  ✅ Proper tool registration verification")
    
    print("\n🔧 TOOL LOADING STRATEGY:")
    print("  1️⃣ Try enhanced_ai_intelligent_tools")
    print("  2️⃣ Fallback to ai_intelligent_tools")
    print("  3️⃣ Fallback to pdok_modular_tools")
    print("  4️⃣ Fallback to pdok_service_discovery_tool")
    print("  5️⃣ Use basic tools + web_search if all fail")
    
    print("\n🧠 HOW FIXED AI INTELLIGENCE WORKS:")
    print("  1. AI checks what tools are actually available")
    print("  2. AI adapts its approach based on available tools")
    print("  3. AI uses web_search as fallback for missing PDOK tools")
    print("  4. AI formats results using json.dumps() with proper structure")
    print("  5. Enhanced search coordinate extraction from execution logs")
    print("  6. Improved JSON response parsing with multiple detection methods")
    
    print("\n🔧 TOOLS STATUS:")
    if tools_available:
        print("  ✅ PDOK intelligent tools loaded successfully")
    else:
        print("  ⚠️ Using basic tools + web_search fallbacks")
    
    print("\nTEST ENDPOINTS:")
    print("  🧪 POST /api/test-ai-intelligence - Test FIXED AI intelligence")
    
    print("\nEXAMPLE QUERIES FOR FIXED AI INTELLIGENCE:")
    print("  • 'Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²'")
    print("  • 'Find large buildings in Amsterdam built before 1950'") 
    print("  • 'What addresses are on Damrak street in Amsterdam?'")
    print("  • 'Show me residential properties in Utrecht'")
    print("  • 'What PDOK services are available?'")
    
    print("\n" + "="*80)
    print(f"🌐 Server endpoints:")
    print(f"  📱 Main app: http://localhost:5000")
    print(f"  🤖 Chat API: POST /api/query")
    print(f"  🗺️ Map state: GET /api/map-state") 
    print(f"  🔄 Reload prompt: POST /api/reload-prompt")
    
    print("\n🧠 THE FIXED AI INTELLIGENCE DIFFERENCE:")
    print("  ✅ AI CHECKS available tools before execution")
    print("  ✅ AI ADAPTS workflow based on tool availability")
    print("  ✅ AI USES web_search fallbacks when PDOK tools missing")
    print("  ✅ PROPER tool registration and verification")
    print("  ✅ ENHANCED error handling for missing tools")
    print("  ✅ MULTIPLE import strategies for tool loading")
    print()
    
    app.run(debug=True, port=5000)