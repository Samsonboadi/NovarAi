# app.py 

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
from tools.enhanced_pdok_location_tool import IntelligentLocationSearchTool, SpecializedAddressSearchTool
from tools.kadaster_tool import KadasterBRKTool, ContactHistoryTool

#Import the new intelligent PDOK agent 
from tools.pdok_intelligent_agent_tool import EnhancedPDOKIntelligentAgent, SmartServiceDiscoveryTool

# Test the PDOK integration
#test_pdok_integration()


# Import the NEW flexible PDOK tools
# from tools.pdok_service_discovery_tool import (
#     PDOKServiceDiscoveryTool,
#     PDOKDataRequestTool,
#     PDOKDataFilterTool,
#     PDOKMapDisplayTool,
#     PDOKBuildingsFlexibleTool
# )

# Test the PDOK integration
#test_pdok_integration()

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
    """Create the map-aware agent with WORKING tools and CORRECT system prompt."""
        # Load system prompt from YAML file
    system_prompt_config = load_system_prompt("static/system_prompt.yml")
    # WORKING TOOLS - using correct names
    tools = [
        # Existing tools
        IntelligentLocationSearchTool(),
        SpecializedAddressSearchTool(),
        analyze_current_map_features,
        
        # New enhanced tools  
        EnhancedPDOKIntelligentAgent(),  # Smart intent detection
        SmartServiceDiscoveryTool(),     # Intelligent service discovery
        
        # Other tools
        DuckDuckGoSearchTool()
    ]

    print("🔧 Creating agent with WORKING PDOK TOOLS:")
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = str(type(tool).__name__)
        print(f"  ✅ {tool_name}")
    
    # Create agent with loaded system prompt
    if system_prompt_config:
        print("✅ Using FIXED YAML system prompt configuration")
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
    """Handle chat queries using the intelligent smolagent with intent-based tool selection."""
    global current_map_state
    
    print("\n" + "="*80)
    print("RECEIVED INTELLIGENT AGENT QUERY - INTENT-BASED TOOL SELECTION")
    print("="*80)
    
    data = request.json
    query_text = data.get('query', '')
    current_features = data.get('current_features', [])
    map_center = data.get('map_center', [5.2913, 52.1326])
    map_zoom = data.get('map_zoom', 8)
    
    print(f"Query text: {query_text}")
    print(f"Current features count: {len(current_features)}")
    print(f"Map context: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E (zoom: {map_zoom})")
    
    # Update map state with frontend data
    if current_features:
        current_map_state["features"] = current_features
    current_map_state["center"] = map_center
    current_map_state["zoom"] = map_zoom
    
    try:
        print("🧠 Running INTELLIGENT MAP-AWARE AGENT with intent-based tool selection...")
        
        # Create intelligent context-aware prompt
        context_prompt = f"""
        User query: "{query_text}"

        Current map context:
        - Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
        - Zoom level: {map_zoom}
        - Features on map: {len(current_features)}

        INTELLIGENT AGENT APPROACH:
        You are an intelligent agent with access to various tools. Analyze the user's request to understand their intent, then select the most appropriate tools based on their descriptions and capabilities.

        AVAILABLE TOOL CATEGORIES:

        🗺️ LOCATION & GEOCODING:
        - find_location_coordinates: Intelligent Dutch location search (addresses, cities, landmarks, postal codes)
        - search_dutch_address: Specialized precise address search with house numbers

        🏢 BUILDING & PROPERTY DATA:
        - enhanced_pdok_intelligent_agent: Smart building/property search with automatic intent detection
        - discover_pdok_services_enhanced: Service discovery with availability checking
        - pdok_intelligent_agent: Dutch geospatial data with automatic service selection

        📊 MAP ANALYSIS & CONTEXT:
        - analyze_current_map_features: Analyze features currently displayed on the map
        - get_map_context_info: Get current map view context and location information
        - answer_map_question: Answer general questions about maps and GIS

        🔍 GENERAL SEARCH:
        - DuckDuckGoSearchTool: Web search for general information

        INSTRUCTIONS:
        1. ANALYZE the user's request to understand what they want
        2. DETERMINE the type of task (location search, building data, map analysis, general question)
        3. SELECT appropriate tools based on their descriptions and capabilities
        4. EXTRACT relevant parameters from the user's natural language request
        5. EXECUTE the selected tools with proper parameters
        6. RETURN results in appropriate format:
           - Geographic data: JSON with text_description and geojson_data
           - Analysis results: Structured text with insights
           - General answers: Plain text response

        EXAMPLES OF INTELLIGENT TOOL SELECTION:

        User: "Show me buildings near Amsterdam Centraal"
        Analysis: Need location + building data
        Tools: find_location_coordinates("Amsterdam Centraal") → enhanced_pdok_intelligent_agent(user_request=...)

        User: "What's at Damrak 1, Amsterdam?"
        Analysis: Need precise address lookup
        Tools: search_dutch_address("Damrak 1, Amsterdam")

        User: "What services are available for building data?"
        Analysis: Need service discovery information
        Tools: discover_pdok_services_enhanced(service_type="bag")

        User: "Analyze the buildings currently on the map"
        Analysis: Need to analyze current map features
        Tools: analyze_current_map_features()

        User: "What is GIS?"
        Analysis: General knowledge question about mapping
        Tools: answer_map_question("What is GIS?")

        Remember: Choose tools based on what the user actually needs, not predefined workflows. Read tool descriptions to understand their capabilities and select the most appropriate ones.
        """
        
        print("🎯 Agent will analyze intent and select appropriate tools automatically...")
        print("📚 Available tools: Location search, Building data, Map analysis, Service discovery, General search")
        
        result = agent.run(context_prompt)
        
        print(f"\n--- INTELLIGENT AGENT RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # Process agent result with enhanced intelligence
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
        
        # Enhanced JSON detection and parsing
        try:
            # Look for structured response with geographic data
            import re
            json_match = re.search(r'\{.*"text_description".*"geojson_data".*\}', result_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
                print("✅ Found structured geographic response")
                
                if isinstance(parsed_response, dict) and 'text_description' in parsed_response and 'geojson_data' in parsed_response:
                    text_description = parsed_response['text_description']
                    geojson_data = parsed_response['geojson_data']
                    
                    # Validate and process geographic data
                    if isinstance(geojson_data, list) and len(geojson_data) > 0:
                        processed_features = []
                        for feature in geojson_data:
                            if isinstance(feature, dict) and 'lat' in feature and 'lon' in feature:
                                # Validate coordinates
                                if feature.get('lat', 0) != 0 and feature.get('lon', 0) != 0:
                                    # Ensure proper serialization
                                    if 'geometry' in feature:
                                        validated_geom = validate_and_fix_geometry(feature['geometry'])
                                        if validated_geom:
                                            feature['geometry'] = validated_geom
                                    
                                    if 'properties' in feature:
                                        feature['properties'] = ensure_json_serializable(feature['properties'])
                                    
                                    processed_features.append(feature)
                        
                        if processed_features:
                            print(f"🗺️ Processed {len(processed_features)} geographic features")
                            
                            # Update map state
                            current_map_state["features"] = processed_features
                            current_map_state["last_updated"] = datetime.now().isoformat()
                            
                            return jsonify({
                                "response": text_description,
                                "geojson_data": processed_features,
                                "agent_type": "intelligent_geographic",
                                "tools_used": "intent_based_selection"
                            })
                    
                    # Text-only geographic response
                    print("📝 Geographic query with text-only response")
                    return jsonify({
                        "response": text_description,
                        "agent_type": "intelligent_text",
                        "tools_used": "intent_based_selection"
                    })
                    
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing note: {e}")
        except Exception as e:
            print(f"⚠️ Response processing note: {e}")
        
        # Search agent execution logs for geographic data (enhanced fallback)
        building_data = None
        text_description = None
        
        if hasattr(agent, 'logs') or hasattr(agent, 'memory'):
            print("🔍 Analyzing agent execution for geographic data...")
            
            # Check multiple log sources
            log_sources = []
            if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
                log_sources.append(('memory.steps', agent.memory.steps))
            if hasattr(agent, 'logs'):
                log_sources.append(('logs', agent.logs))
            
            for source_name, log_entries in log_sources:
                print(f"   📚 Checking {source_name} ({len(log_entries)} entries)...")
                
                for log_index, log_entry in enumerate(reversed(log_entries)):
                    # Multiple methods to find tool results
                    tool_calls_to_check = []
                    
                    # Check various log entry structures
                    if hasattr(log_entry, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.tool_calls)
                    
                    if hasattr(log_entry, 'step_logs'):
                        for step_log in log_entry.step_logs:
                            if hasattr(step_log, 'tool_calls'):
                                tool_calls_to_check.extend(step_log.tool_calls)
                    
                    if hasattr(log_entry, 'action'):
                        if hasattr(log_entry.action, 'tool_calls'):
                            tool_calls_to_check.extend(log_entry.action.tool_calls)
                        elif hasattr(log_entry.action, 'result'):
                            # Direct action result
                            result_data = log_entry.action.result
                            if isinstance(result_data, dict):
                                if 'text_description' in result_data and 'geojson_data' in result_data:
                                    text_description = result_data['text_description']
                                    building_data = result_data['geojson_data']
                                    print(f"🏗️ Found combined response in action.result")
                                    break
                    
                    # Check individual tool call results
                    for tool_call in tool_calls_to_check:
                        if hasattr(tool_call, 'result'):
                            tool_result = tool_call.result
                            
                            # Look for structured geographic response
                            if (isinstance(tool_result, dict) and 
                                'text_description' in tool_result and 
                                'geojson_data' in tool_result):
                                
                                text_description = tool_result['text_description']
                                building_data = tool_result['geojson_data']
                                tool_name = getattr(tool_call, 'tool_name', 'unknown')
                                print(f"🎯 Found structured response from tool: {tool_name}")
                                break
                            
                            # Look for list of geographic features
                            elif isinstance(tool_result, list) and len(tool_result) > 0:
                                first_item = tool_result[0]
                                if (isinstance(first_item, dict) and
                                    'geometry' in first_item and 'lat' in first_item and 
                                    'lon' in first_item and 'name' in first_item and
                                    first_item.get('lat', 0) != 0 and first_item.get('lon', 0) != 0):
                                    
                                    building_data = tool_result
                                    tool_name = getattr(tool_call, 'tool_name', 'geographic_tool')
                                    text_description = f"Found {len(building_data)} features using intelligent tool selection via {tool_name}"
                                    print(f"🗺️ Found geographic feature list from: {tool_name}")
                                    break
                    
                    if building_data and text_description:
                        break
                
                if building_data and text_description:
                    break
        
        # Process found geographic data
        if building_data and text_description:
            print(f"🗺️ Processing intelligent agent geographic response")
            
            if isinstance(building_data, list):
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
                        print(f"❌ Error processing geographic feature: {e}")
                        continue
                
                if serialized_buildings:
                    print(f"✅ Returning intelligent response: text + {len(serialized_buildings)} features")
                    
                    current_map_state["features"] = serialized_buildings
                    current_map_state["last_updated"] = datetime.now().isoformat()
                    
                    return jsonify({
                        "response": text_description,
                        "geojson_data": serialized_buildings,
                        "agent_type": "intelligent_geographic_processed",
                        "tools_used": "intent_based_selection"
                    })
        
        # Handle pure text responses (analysis, questions, etc.)
        print(f"💬 Returning intelligent text response")
        return jsonify({
            "response": str(result_text),
            "agent_type": "intelligent_text",
            "tools_used": "intent_based_selection"
        })
        
    except Exception as e:
        error_msg = f"Intelligent agent error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        print("="*80 + "\n")
        return jsonify({
            "error": error_msg,
            "agent_type": "error",
            "tools_used": "none"
        })

    finally:
        print("🎉 INTELLIGENT AGENT QUERY COMPLETED")
        print("="*80 + "\n")

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



@app.route('/api/test-intelligent-agent', methods=['POST'])
def test_intelligent_agent():
    """Test endpoint for the new intelligent PDOK agent."""
    data = request.json
    user_request = data.get('user_request', 'show verblijfsobject in Groningen')
    max_features = data.get('max_features', 20)
    
    try:
        from tools.pdok_intelligent_agent_tool import PDOKIntelligentAgentTool
        
        agent_tool = PDOKIntelligentAgentTool()
        result = agent_tool.forward(
            user_request=user_request,
            max_features=max_features
        )
        
        return jsonify({
            "success": True,
            "user_request": user_request,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/test-service-discovery', methods=['POST'])
def test_service_discovery():
    """Test endpoint for enhanced service discovery."""
    data = request.json
    service_type = data.get('service_type', 'all')
    check_availability = data.get('check_availability', True)
    
    try:
        from tools.pdok_intelligent_agent_tool import EnhancedPDOKServiceDiscoveryTool
        
        discovery_tool = EnhancedPDOKServiceDiscoveryTool()
        result = discovery_tool.forward(
            service_type=service_type,
            check_availability=check_availability
        )
        
        return jsonify({
            "success": True,
            "service_type": service_type,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
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
    print("🚀 Starting FIXED Map-Aware Flask server with INTELLIGENT PDOK AGENT")
    print("="*80)
    print("FIXED ARCHITECTURE FEATURES:")
    print("  ✅ Intelligent PDOK agent with direct API filtering")
    print("  ✅ Enhanced service discovery with availability checking")
    print("  ✅ Dynamic service and layer selection based on user requests")
    print("  ✅ Proper CQL filtering at API level (no retrieve-then-filter)")
    print("  ✅ Automatic request analysis and endpoint construction")
    print("  ✅ Fixed random building selection issue")
    print("  ✅ Support for verblijfsobject, buildings, parcels, boundaries")
    
    print("\nINTELLIGENT AGENT CAPABILITIES:")
    print("  🤖 pdok_intelligent_agent: Analyzes requests and uses appropriate PDOK service")
    print("  🔍 discover_pdok_services_enhanced: Real-time service availability checking")
    print("  📍 Automatic location detection and coordinate conversion")
    print("  🔧 Direct CQL and spatial filtering")
    print("  🎯 Targeted results without random sampling")
    
    print("\nSOLVES PREVIOUS ISSUES:")
    print("  ✅ No more random building selection across cities")
    print("  ✅ Proper distance-based results around specified locations")
    print("  ✅ Direct API filtering eliminates retrieve-then-filter inefficiency")
    print("  ✅ Dynamic service discovery for any PDOK layer")
    print("  ✅ Proper handling of verblijfsobject, parcels, boundaries")
    print("  ✅ Agent responds correctly to service availability questions")
    
    print("\nTEST ENDPOINTS:")
    print("  🧪 POST /api/test-intelligent-agent - Test intelligent PDOK agent")
    print("  🧪 POST /api/test-service-discovery - Test service discovery")
    print("  🧪 POST /api/test-location - Test location search")
    
    print("\nEXAMPLE QUERIES TO TEST:")
    print("  • 'show me all endpoints from the discovery service'")
    print("  • 'get me some data about verblijfsobject around groningen'") 
    print("  • 'find buildings near Amsterdam with area > 500m²'")
    print("  • 'show cadastral parcels in Utrecht'")
    print("  • 'what PDOK services are available?'")
    
    print("\n" + "="*80)
    print(f"🌐 Server endpoints:")
    print(f"  📱 Main app: http://localhost:5000")
    print(f"  🤖 Chat API: POST /api/query")
    print(f"  🗺️ Map state: GET /api/map-state") 
    print(f"  🔄 Reload prompt: POST /api/reload-prompt")
    print(f"  🧪 Test endpoints: /api/test-*")
    
    print("\n🎯 THE INTELLIGENT AGENT")
    print("  ✅ Service discovery first - understands available endpoints")
    print("  ✅ Request analysis - determines appropriate service and layer")
    print("  ✅ Direct API filtering - uses CQL and bbox parameters")
    print("  ✅ No random sampling - targeted results only")
    print("  ✅ Handles all PDOK data types automatically")
    print()
    
    app.run(debug=True, port=5000)