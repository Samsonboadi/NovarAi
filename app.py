# app.py - Fixed with Proper Tool Docstrings for Flexible PDOK Tools

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

# Import the enhanced PDOK location functionality
from tools.pdok_location import find_location_coordinates, search_dutch_address_pdok, pdok_service, test_pdok_integration
from tools.kadaster_tool import KadasterBRKTool, ContactHistoryTool
from tools.intelligent_pdok_building_tool import IntelligentPDOKBuildingTool


# Import the NEW flexible PDOK tools
from tools.pdok_service_discovery_tool import (
    PDOKServiceDiscoveryTool,
    PDOKDataRequestTool,
    PDOKDataFilterTool,
    PDOKMapDisplayTool,
    PDOKBuildingsFlexibleTool
)

# Test the PDOK integration
test_pdok_integration()

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
    """Load system prompt from YAML file.
    
    Args:
        file_path: Path to the YAML file containing system prompt configuration
        
    Returns:
        Dictionary with system prompt configuration
    """
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
                "suggestions": ["Try searching for buildings in a specific location like 'Groningen' or 'Amsterdam train station'"]
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
            return """GIS (Geographic Information System) is a framework for gathering, managing, and analyzing spatial and geographic data. It combines hardware, software, and data to capture, manage, analyze, and display all forms of geographically referenced information. GIS helps us understand patterns, relationships, and trends in our world by connecting location data with descriptive information."""
        
        elif any(term in question_lower for term in ['what is wgs84', 'coordinate system']):
            return """WGS84 (World Geodetic System 1984) is the standard coordinate system used by GPS and most web mapping applications. It defines locations using latitude and longitude in decimal degrees. In the Netherlands, we also use RD New (EPSG:28992), which is the national coordinate system optimized for accurate measurements within Dutch borders."""
        
        elif any(term in question_lower for term in ['what is pdok', 'pdok']):
            return """PDOK (Publieke Dienstverlening Op de Kaart) is the Dutch national spatial data infrastructure. It provides free access to geographic datasets from Dutch government organizations, including building data (BAG), topographic maps, aerial imagery, and administrative boundaries. It's the authoritative source for Dutch geographic information. The system now uses modular tools for flexible data access."""
        
        elif any(term in question_lower for term in ['what is bag', 'buildings and addresses']):
            return """BAG (Basisregistratie Adressen en Gebouwen) is the Dutch Buildings and Addresses Database. It contains authoritative information about all buildings, addresses, and premises in the Netherlands. Each building has a unique identifier and includes details like construction year, status, area, and precise polygon geometry."""
        
        elif any(term in question_lower for term in ['flexible tools', 'modular approach']):
            return """The new flexible PDOK tools use a modular approach: (1) Service Discovery - finds available PDOK layers and capabilities, (2) Data Request - makes WFS requests to any PDOK service, (3) Data Filter - applies distance, age, and size filters, (4) Map Display - formats results for visualization. This allows the agent to understand PDOK services and construct appropriate queries automatically."""
        
        else:
            return f"I can help with various map and GIS topics including coordinate systems, data formats, spatial analysis, and Dutch geographic data sources. The system now includes flexible modular PDOK tools that can work with any PDOK layer. Could you be more specific about what aspect of mapping or geography you'd like to know about?"
        
    except Exception as e:
        return f"Error answering map question: {str(e)}"

def ensure_json_serializable(obj):
    """Convert any non-JSON serializable objects to JSON serializable format.
    
    Args:
        obj: Object to make JSON serializable
        
    Returns:
        JSON serializable version of the object
    """
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
    """Validate and fix geometry data structure.
    
    Args:
        geometry: Geometry object to validate and fix
        
    Returns:
        Fixed geometry object or None if invalid
    """
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

def create_agent_with_yaml_prompt():
    """Create the map-aware agent with YAML system prompt configuration and flexible PDOK tools.
    
    Returns:
        Configured agent with YAML system prompt and flexible PDOK tools
    """
    
    # Load system prompt from YAML file
    system_prompt_config = load_system_prompt("static/system_prompt.yml")
    
    # Create tools - Now with FLEXIBLE PDOK TOOLS
    tools = [
        find_location_coordinates,        # Enhanced with PDOK Locatieserver
        search_dutch_address_pdok,       # Specialized address search  
        analyze_current_map_features,
        get_map_context_info,
        answer_map_question,
        IntelligentPDOKBuildingTool(),   # NEW: Primary intelligent building search tool
        
        # Keep flexible tools as backup/advanced options
        PDOKServiceDiscoveryTool(),      # Service discovery
        PDOKDataRequestTool(),           # Advanced WFS requests
        PDOKDataFilterTool(),            # Advanced filtering
        PDOKMapDisplayTool(),            # Advanced display formatting
        PDOKBuildingsFlexibleTool(),     # Backup combined tool
        
        # Other tools
        DuckDuckGoSearchTool(),
        ContactHistoryTool(),
        KadasterBRKTool()
    ]

    print("🔧 Creating agent with FLEXIBLE PDOK TOOLS:")
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = str(type(tool).__name__)
        
        if hasattr(tool, 'description'):
            description = tool.description[:60] + "..."
        else:
            description = "No description available"
        
        print(f"  ✅ {tool_name}: {description}")
    
    # Create agent with loaded system prompt
    if system_prompt_config:
        print("✅ Using loaded YAML system prompt configuration")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=15,
            prompt_templates=system_prompt_config,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "shapely.geometry", 
                "shapely.ops", "pyproj", "re", "statistics", "collections", "datetime"
            ]
        )
    else:
        print("⚠️ Using default system prompt - YAML loading failed")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=15,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "shapely.geometry", 
                "shapely.ops", "pyproj", "re", "statistics", "collections", "datetime"
            ]
        )
    
    return agent

# Initialize the agent with flexible PDOK tools
agent = create_agent_with_yaml_prompt()

# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries using the smolagent with flexible PDOK tools."""
    global current_map_state
    
    print("\n" + "="*60)
    print("RECEIVED MAP-AWARE QUERY REQUEST - FLEXIBLE PDOK TOOLS")
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
    
    try:
        print("🏗️ Running enhanced map-aware agent with flexible PDOK tools...")
        
        # Create context-aware prompt
        context_prompt = f"""
User query: "{query_text}"

Current map context:
- Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
- Zoom level: {map_zoom}
- Features on map: {len(current_features)}

IMPORTANT: The system now uses FLEXIBLE MODULAR PDOK TOOLS:

1. discover_pdok_services: Find available PDOK WFS services and layers
2. request_pdok_data: Make flexible WFS requests to any PDOK service
3. filter_pdok_data: Apply distance, age, area, and other filters
4. format_pdok_for_map: Format results for map display
5. get_pdok_buildings_flexible: Combined tool for building searches

WORKFLOW for building searches:
- Use get_pdok_buildings_flexible for simple building queries
- For complex queries, use the individual tools in sequence
- The tools can handle any PDOK layer, not just buildings

For GEOGRAPHIC queries: Use tools and return JSON with text_description and geojson_data
For GENERAL questions: Simply answer the question with plain text using final_answer()

Please respond to the user's query appropriately based on the query type.
"""
        
        result = agent.run(context_prompt)
        
        print(f"\n--- AGENT RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # Try to parse the result as JSON first
        parsed_response = None
        if hasattr(result, 'content'):
            result_text = result.content
        elif hasattr(result, 'text'):  
            result_text = result.text
        elif isinstance(result, str):
            result_text = result
        else:
            result_text = str(result)
        
        print(f"Result text preview: {result_text[:200]}...")
        
        # Try to parse as JSON
        try:
            # Look for JSON structure in the response
            import re
            json_match = re.search(r'\{.*"text_description".*"geojson_data".*\}', result_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
                print("✅ Successfully parsed JSON response with text_description and geojson_data")
                
                # Validate the structure
                if isinstance(parsed_response, dict) and 'text_description' in parsed_response and 'geojson_data' in parsed_response:
                    text_description = parsed_response['text_description']
                    geojson_data = parsed_response['geojson_data']
                    
                    # Validate and process geojson_data
                    if isinstance(geojson_data, list) and len(geojson_data) > 0:
                        # Process each feature to ensure proper format
                        processed_features = []
                        for feature in geojson_data:
                            if isinstance(feature, dict) and 'lat' in feature and 'lon' in feature:
                                # Ensure the geometry is properly formatted
                                if 'geometry' in feature:
                                    validated_geom = validate_and_fix_geometry(feature['geometry'])
                                    if validated_geom:
                                        feature['geometry'] = validated_geom
                                
                                # Ensure properties are serializable
                                if 'properties' in feature:
                                    feature['properties'] = ensure_json_serializable(feature['properties'])
                                
                                # Validate coordinates
                                if feature.get('lat', 0) != 0 and feature.get('lon', 0) != 0:
                                    processed_features.append(feature)
                        
                        if processed_features:
                            print(f"🗺️ Processed {len(processed_features)} valid features for map display")
                            
                            # Update map state
                            current_map_state["features"] = processed_features
                            current_map_state["last_updated"] = datetime.now().isoformat()
                            
                            # Return the separated response
                            return jsonify({
                                "response": text_description,
                                "geojson_data": processed_features
                            })
                    
                    # If geojson_data is empty or invalid, return just the text
                    print("⚠️ GeoJSON data is empty or invalid, returning text only")
                    return jsonify({"response": text_description})
                    
            else:
                print("❌ No JSON structure found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
        except Exception as e:
            print(f"❌ Error processing JSON response: {e}")
        
        # Search for building data in agent execution logs (fallback)
        building_data = None
        text_description = None
        
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
                    # Multiple ways to find tool calls
                    tool_calls_to_check = []
                    
                    # Method 1: Direct tool_calls attribute
                    if hasattr(log_entry, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.tool_calls)
                    
                    # Method 2: step_logs -> tool_calls
                    if hasattr(log_entry, 'step_logs'):
                        for step_log in log_entry.step_logs:
                            if hasattr(step_log, 'tool_calls'):
                                tool_calls_to_check.extend(step_log.tool_calls)
                    
                    # Method 3: action or tool_call attributes (for new memory structure)
                    if hasattr(log_entry, 'action') and hasattr(log_entry.action, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.action.tool_calls)
                    
                    # Method 4: Direct action.result (for new memory structure)
                    if hasattr(log_entry, 'action') and hasattr(log_entry.action, 'result'):
                        result_data = log_entry.action.result
                        if isinstance(result_data, dict):
                            if 'text_description' in result_data and 'geojson_data' in result_data:
                                text_description = result_data['text_description']
                                building_data = result_data['geojson_data']
                                print(f"🏗️  ✅ Found combined response in action.result")
                                break
                    
                    # Method 5: Check individual tool calls
                    for tool_call in tool_calls_to_check:
                        if hasattr(tool_call, 'result'):
                            tool_result = tool_call.result
                            
                            # Check if this is our combined response format
                            if (isinstance(tool_result, dict) and 
                                'text_description' in tool_result and 
                                'geojson_data' in tool_result):
                                
                                text_description = tool_result['text_description']
                                building_data = tool_result['geojson_data']
                                print(f"🏗️  ✅ Found combined response in tool call result")
                                break
                            
                            # Legacy format check (array of buildings)
                            elif (isinstance(tool_result, list) and len(tool_result) > 0):
                                first_item = tool_result[0]
                                if (isinstance(first_item, dict) and
                                    'geometry' in first_item and 'lat' in first_item and 
                                    'lon' in first_item and 'name' in first_item and
                                    first_item.get('lat', 0) != 0 and first_item.get('lon', 0) != 0):
                                    
                                    # Check that this is NOT mock data
                                    if not any('mock' in str(first_item).lower() for first_item in tool_result):
                                        building_data = tool_result
                                        text_description = f"Found {len(building_data)} real buildings from flexible PDOK search and displayed them on the map."
                                        print(f"🏗️  ✅ Found building data format: {len(building_data)} buildings")
                                        break
                    
                    if building_data and text_description:
                        break
                
                if building_data and text_description:
                    break
        
        # If we found combined data, return it properly formatted
        if building_data and text_description:
            print(f"🗺️ Processing combined response with {len(building_data) if isinstance(building_data, list) else 'unknown'} buildings")
            
            # Validate and serialize building data
            if isinstance(building_data, list):
                serialized_buildings = []
                for building in building_data:
                    try:
                        if isinstance(building, dict):
                            # Skip mock data
                            if any('mock' in str(value).lower() for value in building.values()):
                                print("⚠️ Skipping mock data entry")
                                continue
                                
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
                    print(f"✅ Returning flexible combined response: text + {len(serialized_buildings)} buildings")
                    
                    current_map_state["features"] = serialized_buildings
                    current_map_state["last_updated"] = datetime.now().isoformat()
                    
                    return jsonify({
                        "response": text_description,
                        "geojson_data": serialized_buildings
                    })
        
        # Handle text-only responses (analysis, questions, etc.)
        print(f"💬 Returning text-only response: {str(result_text)[:200]}...")
        return jsonify({"response": str(result_text)})
        
    except Exception as e:
        error_msg = f"Flexible map-aware agent error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        print("="*60 + "\n")
        return jsonify({"error": error_msg})

@app.route('/api/map-state', methods=['GET'])
def get_map_state():
    """Get current map state for debugging."""
    global current_map_state
    return jsonify(current_map_state)

@app.route('/api/reload-prompt', methods=['POST'])
def reload_system_prompt():
    """Reload the system prompt from YAML file and recreate the agent."""
    global agent
    try:
        print("🔄 Reloading system prompt from YAML...")
        agent = create_agent_with_yaml_prompt()
        return jsonify({
            "success": True,
            "message": "System prompt reloaded successfully with FLEXIBLE PDOK TOOLS"
        })
    except Exception as e:
        error_msg = f"Error reloading system prompt: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        })

@app.route('/api/test-location', methods=['POST'])
def test_location_search():
    """Test endpoint for the enhanced location search.
    
    Expects JSON body with 'query' field containing location to search for.
    """
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "No query provided"})
    
    try:
        print(f"🧪 Testing location search for: '{query}'")
        result = find_location_coordinates(query)
        
        return jsonify({
            "query": query,
            "result": result,
            "success": not result.get('error'),
            "coordinates": [result.get('lat', 0), result.get('lon', 0)] if not result.get('error') else None
        })
        
    except Exception as e:
        return jsonify({
            "query": query,
            "error": str(e),
            "success": False
        })

@app.route('/api/test-pdok-services', methods=['POST'])
def test_pdok_services():
    """Test endpoint for PDOK service discovery."""
    try:
        from tools.pdok_service_discovery_tool import PDOKServiceDiscoveryTool
        
        discovery_tool = PDOKServiceDiscoveryTool()
        result = discovery_tool.forward("all")
        
        return jsonify({
            "success": True,
            "services": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/test-flexible-buildings', methods=['POST'])
def test_flexible_buildings():
    """Test endpoint for flexible building search.
    
    Expects JSON body with optional parameters:
    - location: Location to search (default: 'Groningen')
    - max_year: Maximum construction year for age filtering
    - radius_km: Search radius in kilometers (default: 5.0)
    """
    data = request.json
    location = data.get('location', 'Groningen')
    max_year = data.get('max_year', None)
    radius_km = data.get('radius_km', 5.0)
    
    try:
        from tools.pdok_service_discovery_tool import PDOKBuildingsFlexibleTool
        
        flexible_tool = PDOKBuildingsFlexibleTool()
        result = flexible_tool.forward(
            location=location,
            max_features=10,
            max_year=max_year,
            radius_km=radius_km
        )
        
        return jsonify({
            "success": True,
            "location": location,
            "max_year": max_year,
            "radius_km": radius_km,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    print("🚀 Starting Enhanced Map-Aware Flask server with FLEXIBLE PDOK TOOLS")
    print("="*80)
    print("NEW FLEXIBLE CAPABILITIES:")
    print("  ✅ Modular PDOK tools for any WFS service and layer")
    print("  ✅ Service discovery - finds available PDOK layers automatically")
    print("  ✅ Flexible data requests - works with any PDOK WFS endpoint")
    print("  ✅ Advanced filtering - distance, age, area, and custom criteria")
    print("  ✅ Smart map formatting - proper descriptions and metadata")
    print("  ✅ Combined building tool - simple interface for complex operations")
    print("  ✅ Better coordinate handling and distance calculations")
    print("  ✅ Enhanced error handling and debugging")
    print("  ✅ FIXED: Proper tool docstrings for smolagents compatibility")
    
    print("\nFLEXIBLE TOOL ARCHITECTURE:")
    print("  🔍 discover_pdok_services: Find available PDOK WFS services")
    print("  🌐 request_pdok_data: Make flexible WFS requests to any service")
    print("  🔽 filter_pdok_data: Apply advanced filters to results")
    print("  🗺️ format_pdok_for_map: Format data for map display")
    print("  🏗️ get_pdok_buildings_flexible: Combined building search tool")
    
    print("\nSOLVES PREVIOUS ISSUES:")
    print("  ✅ No more 0 buildings found - better distance calculations")
    print("  ✅ Proper coordinate system handling - RD New ↔ WGS84")
    print("  ✅ Flexible filtering - age, area, distance criteria")
    print("  ✅ Agent can understand PDOK services automatically")
    print("  ✅ Works with any PDOK layer, not just buildings")
    print("  ✅ Detailed logging for debugging")
    print("  ✅ FIXED: Tool docstring compatibility with smolagents")
    
    print("\nTEST ENDPOINTS:")
    print("  🧪 POST /api/test-location - Test location search")
    print("  🧪 POST /api/test-pdok-services - Test service discovery")
    print("  🧪 POST /api/test-flexible-buildings - Test flexible building search")
    
    print("\nEXAMPLE QUERIES TO TEST:")
    print("  • 'Show me 20 buildings in Groningen older than 100 years'")
    print("  • 'Find buildings near Amsterdam train station built before 1950'")
    print("  • 'Show historic buildings in Utrecht within 3km radius'")
    print("  • 'Buildings in Rotterdam larger than 500m² from the 1960s'")
    print("  • 'What PDOK services are available?'")
    
    print("\n" + "="*80)
    print(f"🌐 Server endpoints:")
    print(f"  📱 Main app: http://localhost:5000")
    print(f"  🤖 Chat API: POST /api/query")
    print(f"  🗺️ Map state: GET /api/map-state") 
    print(f"  🔄 Reload prompt: POST /api/reload-prompt")
    print(f"  🧪 Test endpoints: /api/test-*")
    
    print("\n🔧 TROUBLESHOOTING:")
    print("  If you get import errors:")
    print("    1. Make sure tools/pdok_service_discovery_tool.py exists")
    print("    2. Check that PyProj is installed: pip install pyproj")
    print("    3. Verify all tool files are in the tools/ directory")
    
    print("\n🎯 THE DOCSTRING FIX:")
    print("  ✅ All @tool decorated functions now have proper parameter descriptions")
    print("  ✅ This resolves the DocstringParsingException error")
    print("  ✅ smolagents can now generate JSON schemas correctly")
    print()
    
    app.run(debug=True, port=5000)