# app.py - AI Intent Detection (AI analyzes and decides, not tools)

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
    """Create the map-aware agent where AI does the intent detection."""
    
    # Try to import the enhanced intelligent tools with attribute discovery
    try:
        from tools.enhanced_ai_intelligent_tools import (
            EnhancedPDOKServiceDiscoveryTool,
            LocationSearchTool,
            PDOKDataRequestTool
        )
        
        intelligent_tools = [
            EnhancedPDOKServiceDiscoveryTool(),  # Enhanced with attribute discovery
            LocationSearchTool(),                # AI uses this to find coordinates  
            PDOKDataRequestTool(),               # AI uses this to make requests
        ]
        print("✅ Successfully imported ENHANCED intelligent tools with attribute discovery")
        tools_available = True
        
    except ImportError as e:
        print(f"⚠️ Could not import enhanced tools: {e}")
        print("🔄 Trying original tools...")
        
        try:
            from tools.ai_intelligent_tools import (
                PDOKServiceDiscoveryTool,
                LocationSearchTool,
                PDOKDataRequestTool
            )
            
            intelligent_tools = [
                PDOKServiceDiscoveryTool(),       # Original version
                LocationSearchTool(),            
                PDOKDataRequestTool(),           
            ]
            print("✅ Using original intelligent tools")
            tools_available = True
            
        except ImportError as e2:
            print(f"⚠️ Could not import any intelligent tools: {e2}")
            intelligent_tools = []
            tools_available = False
    
    # Combine all tools for the AI to use
    tools = []
    tools.extend(intelligent_tools)
    
    # Add built-in tools
    tools.extend([
        analyze_current_map_features,
        get_map_context_info,
        answer_map_question,
        DuckDuckGoSearchTool()
    ])

    print(f"🧠 Creating AI-INTELLIGENT agent with {len(tools)} tools:")
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = str(type(tool).__name__)
        print(f"  ✅ {tool_name}")
    
    # Load system prompt optimized for AI intelligence
    system_prompt_config = load_system_prompt("static/system_prompt.yml")
    
    # Create agent with AI-intelligent configuration
    if system_prompt_config:
        print("✅ Using AI-INTELLIGENT system prompt configuration")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=20,  # More steps for AI analysis
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
    
    return agent, tools_available

# Initialize the agent with AI intelligence
agent, tools_available = create_agent_with_ai_intelligence()

# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('base.html')




def extract_search_coordinates_from_agent_logs(agent):
    """Extract search coordinates directly from agent execution logs."""
    try:
        if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
            print("🔍 Searching for location coordinates in agent memory...")
            
            for step in agent.memory.steps:
                if hasattr(step, 'tool_calls'):
                    for tool_call in step.tool_calls:
                        tool_name = getattr(tool_call, 'tool_name', 'unknown')
                        
                        if tool_name == 'search_location_coordinates' and hasattr(tool_call, 'result'):
                            location_result = tool_call.result
                            
                            if (isinstance(location_result, dict) and 
                                not location_result.get('error') and
                                'lat' in location_result and 'lon' in location_result):
                                
                                return {
                                    "lat": float(location_result['lat']),
                                    "lon": float(location_result['lon']),
                                    "name": location_result.get('name', 'Search Location')
                                }
        return None
    except Exception as e:
        print(f"❌ Error extracting search coordinates: {e}")
        return None

        
@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries using AI INTELLIGENCE for intent detection."""
    global current_map_state
    
    print("\n" + "="*80)
    print("🧠 AI INTELLIGENCE - AI ANALYZES AND DECIDES")
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
        print("🧠 Running AI with INTELLIGENCE-BASED INTENT DETECTION...")
        
        # Create AI-intelligent context prompt
        context_prompt = f"""
        User query: "{query_text}"

        Current map context:
        - Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
        - Zoom level: {map_zoom}
        - Features on map: {len(current_features)}

        AI INTELLIGENCE INSTRUCTIONS:
        You are an intelligent AI that can analyze user requests and understand what they want.
        
        🧠 YOUR INTELLIGENCE PROCESS:
        1. ANALYZE the user query to understand their intent
        2. EXTRACT any parameters from their request (locations, filters, constraints)
        3. DISCOVER what PDOK services are available using the tools
        4. UNDERSTAND what data is available at each endpoint
        5. CONSTRUCT the appropriate API calls using the right tools
        6. PROCESS and format the results for map display

        🔧 AVAILABLE TOOLS FOR YOU TO USE:
        - discover_pdok_services: Learn what PDOK services and layers are available
        - search_location_coordinates: Find coordinates for mentioned locations
        - request_pdok_data: Make WFS requests to PDOK services
        - analyze_current_map_features: Analyze current map data
        - get_map_context_info: Get current map context
        - answer_map_question: Answer general map/GIS questions

        🎯 INTELLIGENT WORKFLOW:
        
        For geospatial data requests (buildings, addresses, parcels):
        1. First use discover_pdok_services() to understand available services
        2. Analyze the user query to determine what type of data they want
        3. If location mentioned, use search_location_coordinates() to get coordinates
        4. Select appropriate service URL and layer based on your analysis
        5. Extract any filters from the user request (area, age, etc.)
        6. Use request_pdok_data() with the parameters you determined
        7. Format results as JSON with text_description and geojson_data
        
        For service questions:
        1. Use discover_pdok_services() to get current information
        2. Format as informative response
        
        For location questions:
        1. Use search_location_coordinates() to find the location
        2. Provide coordinates and description
        
        For general questions:
        1. Use answer_map_question() for general map/GIS topics

        EXAMPLE INTELLIGENT ANALYSIS:
        
        User: "Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²"
        
        Your analysis:
        - Intent: Buildings data
        - Location: "Leonard Springerlaan 37, Groningen" 
        - Filter: Area > 300m²
        - Action: Discover services → Find location → Request building data with filters
        
        Your steps:
        1. discover_pdok_services() to learn about available services
        2. search_location_coordinates("Leonard Springerlaan 37, Groningen") to get coordinates
        3. Determine that BAG service with bag:pand layer is appropriate for buildings
        4. Create CQL filter for area > 300m² (oppervlakte_min >= 300)
        5. request_pdok_data() with BAG URL, bag:pand layer, coordinates, and filter
        6. Format results as JSON response

        CRITICAL REQUIREMENTS:
        - ALWAYS import json when working with geographic data
        - ALWAYS use json.dumps() for structured responses with geojson_data
        - Let YOUR INTELLIGENCE guide the process, not predefined workflows
        - Extract parameters from user requests using your analysis
        - Use the tools based on what YOU determine is needed
        - Think step by step and explain your reasoning

        Now analyze the user's request using your AI intelligence and use the appropriate tools.
        """
        
        print("🎯 AI will analyze query and determine approach...")
        print("🔧 AI has access to discovery, location, and data request tools")
        
        result = agent.run(context_prompt)
        
        print(f"\n--- AI INTELLIGENCE RESULT DEBUG ---")
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
        
        print(f"Result text preview: {result_text[:200]}...")
        
        # FIXED: Extract search coordinates directly from agent logs
        search_location = extract_search_coordinates_from_agent_logs(agent)
        
        # Enhanced JSON detection for AI-generated responses
        try:
            import re
            json_match = re.search(r'\{.*"text_description".*"geojson_data".*\}', result_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
                print("✅ Found AI-generated structured response")
                
                if isinstance(parsed_response, dict) and 'text_description' in parsed_response and 'geojson_data' in parsed_response:
                    text_description = parsed_response['text_description']
                    geojson_data = parsed_response['geojson_data']
                    
                    # Validate and process geographic data
                    if isinstance(geojson_data, list) and len(geojson_data) > 0:
                        processed_features = []
                        for feature in geojson_data:
                            if isinstance(feature, dict) and 'lat' in feature and 'lon' in feature:
                                if feature.get('lat', 0) != 0 and feature.get('lon', 0) != 0:
                                    if 'geometry' in feature:
                                        validated_geom = validate_and_fix_geometry(feature['geometry'])
                                        if validated_geom:
                                            feature['geometry'] = validated_geom
                                    
                                    if 'properties' in feature:
                                        feature['properties'] = ensure_json_serializable(feature['properties'])
                                    
                                    processed_features.append(feature)
                        
                        if processed_features:
                            print(f"🗺️ AI generated {len(processed_features)} valid features")
                            
                            current_map_state["features"] = processed_features
                            current_map_state["last_updated"] = datetime.now().isoformat()
                            
                            # FIXED: Include search location in response
                            response_data = {
                                "response": text_description,
                                "geojson_data": processed_features,
                                "agent_type": "ai_intelligent_geographic",
                                "ai_method": "intelligent_analysis",
                                "tools_used": "ai_intelligence"
                            }
                            
                            if search_location:
                                response_data["search_location"] = search_location
                                print(f"📍 Including search location: {search_location['name']} at {search_location['lat']}, {search_location['lon']}")
                            
                            return jsonify(response_data)
                    
                    # Text-only AI response
                    print("📝 AI query with text-only response")
                    response_data = {
                        "response": text_description,
                        "agent_type": "ai_intelligent_text",
                        "ai_method": "intelligent_analysis",
                        "tools_used": "ai_intelligence"
                    }
                    
                    if search_location:
                        response_data["search_location"] = search_location
                    
                    return jsonify(response_data)
                    
        except json.JSONDecodeError:
            pass
        except Exception:
            pass
        
        # Continue with existing logic for other response types...
        # (Keep the rest of the existing function)
        
        # FALLBACK: Always include search location if found
        if search_location:
            print(f"📍 Adding search location to fallback response: {search_location['name']}")
        
        # Handle pure text responses from AI intelligence
        print(f"💬 Returning AI intelligent text response")
        response_data = {
            "response": str(result_text),
            "agent_type": "ai_intelligent_text",
            "ai_method": "intelligent_analysis",
            "tools_used": "ai_intelligence"
        }
        
        if search_location:
            response_data["search_location"] = search_location
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"AI intelligence error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({
            "error": error_msg,
            "agent_type": "error",
            "tools_used": "none"
        })

    finally:
        print("🎉 AI INTELLIGENCE QUERY COMPLETED")
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
            "message": "System prompt reloaded successfully with AI INTELLIGENCE"
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
        print(f"🧪 Testing AI intelligence with: '{test_query}'")
        
        # Simple test of AI analysis
        return jsonify({
            "success": True,
            "query": test_query,
            "message": "AI intelligence system is ready to analyze this query",
            "ai_approach": "The AI will analyze the query, discover services, find locations, and construct appropriate API calls",
            "tools_available": tools_available
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    print("🚀 Starting AI-INTELLIGENT Map-Aware Flask server")
    print("="*80)
    print("🧠 AI INTELLIGENCE ARCHITECTURE:")
    print("  ✅ AI analyzes user queries for intent (NOT tools)")
    print("  ✅ AI extracts parameters and filters from requests")
    print("  ✅ AI discovers available PDOK services using tools")
    print("  ✅ AI constructs appropriate API calls based on analysis")
    print("  ✅ AI makes intelligent decisions about service selection")
    print("  ✅ AI formats results for map display")
    
    print("\n🧠 HOW AI INTELLIGENCE WORKS:")
    print("  1. AI receives user query")
    print("  2. AI analyzes intent and extracts parameters")  
    print("  3. AI uses discover_pdok_services to learn available endpoints")
    print("  4. AI uses search_location_coordinates if location mentioned")
    print("  5. AI selects appropriate service/layer based on analysis")
    print("  6. AI constructs filters based on user request")
    print("  7. AI uses request_pdok_data with determined parameters")
    print("  8. AI formats results for map display")
    
    print("\n🔧 TOOLS AVAILABLE FOR AI:")
    if tools_available:
        print("  🔍 discover_pdok_services: For AI to learn about endpoints")
        print("  📍 search_location_coordinates: For AI to find locations")
        print("  🌐 request_pdok_data: For AI to make WFS requests")
    else:
        print("  📊 Basic analysis and question answering tools")
    
    print("  📊 analyze_current_map_features: For map analysis")
    print("  🗺️ get_map_context_info: For map context")
    print("  ❓ answer_map_question: For general questions")
    
    print("\nTEST ENDPOINTS:")
    print("  🧪 POST /api/test-ai-intelligence - Test AI intelligence")
    
    print("\nEXAMPLE QUERIES FOR AI INTELLIGENCE:")
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
    
    print("\n🧠 THE AI INTELLIGENCE DIFFERENCE:")
    print("  ✅ AI ANALYZES user requests (not tools)")
    print("  ✅ AI EXTRACTS parameters and filters")
    print("  ✅ AI DISCOVERS services dynamically")
    print("  ✅ AI CONSTRUCTS API calls intelligently")
    print("  ✅ AI MAKES all decisions based on analysis")
    print()
    
    app.run(debug=True, port=5000)