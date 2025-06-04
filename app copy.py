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
from tools.flexible_ai_driven_spatial_tools import (
    FlexibleSpatialDataTool,
    FlexibleSpatialAnalysisTool    
)
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
    from tools.coordinate_conversion_tool import CoordinateConversionTool , CreateRDBoundingBoxTool
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
        DuckDuckGoSearchTool(),
        CoordinateConversionTool(),
        FlexibleSpatialDataTool(),
        FlexibleSpatialAnalysisTool()

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


@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries using TRUE AI FLEXIBILITY with minimal guidance."""
    global current_map_state
    
    print("\n" + "="*80)
    print("🧠 TRUE AI FLEXIBILITY - AI DECIDES EVERYTHING")
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
        print("🧠 Running AI with COMPLETE FLEXIBILITY...")
        
        # MINIMAL context prompt - let AI decide everything
        minimal_context_prompt = f"""
        User query: "{query_text}"

        Current map context:
        - Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
        - Zoom level: {map_zoom}
        - Features currently on map: {len(current_features)}

        You are an intelligent AI assistant with access to tools for spatial analysis and geospatial data.

        MANDATORY WORKFLOW - Follow this exact sequence:

        1. ANALYZE USER QUERY
        - Identify what type of data is needed (buildings, addresses, parcels, etc.)
        - Identify any specific filters mentioned (area, year, type, location, etc.)
        - Identify the location or area of interest

        2. DISCOVER AVAILABLE ATTRIBUTES - ALWAYS DO THIS FIRST
        - BEFORE making any data requests, you MUST use discover_pdok_services tool
        - Find out what services are available and what their exact attribute names are
        - Pay attention to the exact spelling and format of attribute names
        - Note which service URLs and layer names to use

        3. FIND COORDINATES (if location mentioned)
        - Use search_location_coordinates to find coordinates for mentioned addresses/locations
        - Convert to proper format for the service

        4. REQUEST DATA WITH CORRECT ATTRIBUTES
        - Use the EXACT attribute names discovered in step 2
        - Do not guess or assume attribute names
        - Use the correct service URL and layer name from step 2

        5. ERROR HANDLING - If any step fails:
        - If data request fails due to wrong attributes, go back to step 2
        - Re-discover the service attributes
        - Correct the attribute names and try again
        - Do not give up after first failure

        CRITICAL RULES:
        ❌ NEVER guess attribute names like "oppervlakte_min", "area", "bouwjaar" etc.
        ❌ NEVER skip the discover_pdok_services step
        ❌ NEVER assume you know the correct attribute names
        ✅ ALWAYS discover attributes first before making any data request
        ✅ ALWAYS use the EXACT attribute names found by discover_pdok_services
        ✅ ALWAYS retry with corrected attributes if first attempt fails

        TECHNICAL REQUIREMENTS:
        - PDOK services use Dutch projected coordinates EPSG:28992
        - Import 'json' when working with geographic data
        - Format geographic responses as GeoJSON

        RESPONSE FORMAT:
        Alwayd return this JSON structures:
        - {{"text_description": "...", "geojson_data": [...]}}


        EXAMPLE WORKFLOW:
        User asks: "Show buildings with area > 300m²"

        Step 1: I need building data with area filtering
        Step 2: discover_pdok_services() → Find BAG service has "oppervlakte" attribute (not "area")
        Step 3: No location mentioned, skip coordinates
        Step 4: Use fetch_pdok_data with filter "oppervlakte > 300" (exact attribute name)
        Step 5: If error "unknown attribute oppervlakte", retry discover_pdok_services and find correct name

        START WITH: discover_pdok_services tool to find available services and attributes.
        """
        
        print("🎯 AI has complete freedom to analyze and respond...")
        print("🔧 No predefined workflows - AI chooses everything")

        result = agent.run(minimal_context_prompt)
        
        print(f"\n--- AI FLEXIBILITY RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # ENHANCED DEBUG: Print the FULL result to see what we're getting
        print(f"FULL RESULT: {result}")
        if isinstance(result, dict):
            print(f"Result keys: {list(result.keys())}")
            for key, value in result.items():
                if isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                    if len(value) > 0:
                        print(f"    First item type: {type(value[0])}")
                        if isinstance(value[0], dict):
                            print(f"    First item keys: {list(value[0].keys())}")
                else:
                    print(f"  {key}: {type(value)} - {str(value)[:100]}...")

        # Handle different result types properly
        structured_response = None
        result_text = None
        
        # Check if result is already a structured dictionary
        if isinstance(result, dict):
            print("✅ AI returned structured dictionary response")
            structured_response = result
            result_text = str(result)
        else:
            # Extract text from various result formats
            if hasattr(result, 'content'):
                result_text = result.content
            elif hasattr(result, 'text'):  
                result_text = result.text
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            print(f"Result text preview: {result_text[:200]}...")
            
            # Try to parse JSON from text if not already structured
            try:
                import re
                
                # Look for various JSON patterns the AI might use
                json_patterns = [
                    r'\{.*"text_description".*"geojson_data".*\}',
                    r'\{.*"description".*"features".*\}',
                    r'\{.*"response".*"data".*\}',
                    r'\{.*"message".*"results".*\}'
                ]
                
                for pattern in json_patterns:
                    json_match = re.search(pattern, result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            parsed_response = json.loads(json_str)
                            if isinstance(parsed_response, dict):
                                structured_response = parsed_response
                                print(f"✅ Found AI-generated structured response with pattern: {pattern[:30]}...")
                                break
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                print(f"⚠️ Error detecting structured response: {e}")
        
        # Process structured response if found
        if structured_response:
            print(f"🔍 Processing structured response: {list(structured_response.keys())}")
            
            # Find text description
            text_fields = ['text_description', 'description', 'response', 'message', 'summary']
            response_text = None
            
            for text_field in text_fields:
                if text_field in structured_response:
                    response_text = structured_response[text_field]
                    print(f"✅ Found text description in field: {text_field}")
                    break
            
            # ENHANCED: Extract and process geographic data
            processed_features = extract_and_process_geographic_data(structured_response)
            
            if processed_features and len(processed_features) > 0:
                print(f"🗺️ Successfully processed geographic data: {len(processed_features)} features")
                
                # Update global state
                current_map_state["features"] = processed_features
                current_map_state["last_updated"] = datetime.now().isoformat()
                
                return jsonify({
                    "response": response_text or "AI analysis completed with geographic results.",
                    "geojson_data": processed_features,
                    "agent_type": "ai_flexible_geographic",
                    "ai_method": "flexible_analysis",
                    "tools_used": "ai_choice"
                })
            else:
                print("❌ No valid geographic data found in structured response")
                
                # Log what was actually found for debugging
                for field_name, field_value in structured_response.items():
                    print(f"   Field '{field_name}': {type(field_value)}")
                    if isinstance(field_value, dict):
                        print(f"     Dict keys: {list(field_value.keys())}")
                        if 'type' in field_value:
                            print(f"     Type: {field_value['type']}")
                        if 'features' in field_value:
                            print(f"     Features count: {len(field_value.get('features', []))}")
            
            # Structured response without geographic data but with text
            if response_text:
                print("📝 AI generated structured text response")
                return jsonify({
                    "response": response_text,
                    "agent_type": "ai_flexible_text",
                    "ai_method": "flexible_analysis", 
                    "tools_used": "ai_choice"
                })
        
        # ENHANCED: Search agent execution logs more thoroughly
        print("🔍 Searching agent logs for geographic data...")
        geographic_data = None
        description_text = None
        
        # Check agent memory for tool results
        if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
            log_entries = agent.memory.steps
            print(f"   📚 Checking memory.steps ({len(log_entries)} entries)...")
            
            for step_idx, log_entry in enumerate(reversed(log_entries)):
                print(f"   Step {step_idx}: {type(log_entry)}")
                
                # Check for any tool call results
                tool_calls_to_check = []
                
                if hasattr(log_entry, 'tool_calls'):
                    tool_calls_to_check.extend(log_entry.tool_calls)
                    print(f"     Found {len(log_entry.tool_calls)} tool calls")
                
                if hasattr(log_entry, 'action'):
                    if hasattr(log_entry.action, 'tool_calls'):
                        tool_calls_to_check.extend(log_entry.action.tool_calls)
                        print(f"     Found {len(log_entry.action.tool_calls)} action tool calls")
                    elif hasattr(log_entry.action, 'result'):
                        result_data = log_entry.action.result
                        print(f"     Action result type: {type(result_data)}")
                        if isinstance(result_data, dict):
                            print(f"     Action result keys: {list(result_data.keys())}")
                            # Look for any geographic data pattern
                            geographic_data, description_text = _extract_geographic_data_flexible(result_data)
                            if geographic_data:
                                print(f"🧠 Found geographic data in action.result: {len(geographic_data)} features")
                                break
                
                # Check individual tool call results
                for tool_call_idx, tool_call in enumerate(tool_calls_to_check):
                    if hasattr(tool_call, 'result'):
                        tool_result = tool_call.result
                        tool_name = getattr(tool_call, 'tool_name', f'tool_{tool_call_idx}')
                        
                        print(f"     Tool '{tool_name}' result type: {type(tool_result)}")
                        
                        if isinstance(tool_result, dict):
                            print(f"     Tool '{tool_name}' result keys: {list(tool_result.keys())}")
                            
                            # Flexible extraction of geographic data
                            geo_data, desc_text = _extract_geographic_data_flexible(tool_result)
                            if geo_data:
                                geographic_data = geo_data
                                description_text = desc_text or f"AI analysis completed using {tool_name}"
                                print(f"🎯 Found geographic data from tool '{tool_name}': {len(geo_data)} features")
                                break
                
                if geographic_data:
                    break
        
        # Process any geographic data found in logs
        if geographic_data:
            print(f"🗺️ Processing geographic data from logs: {len(geographic_data)} features")
            
            if isinstance(geographic_data, list):
                serialized_features = []
                for item in geographic_data:
                    try:
                        if isinstance(item, dict):
                            serialized_item = ensure_json_serializable(item)
                            
                            # Flexible validation
                            if _is_valid_geographic_feature(serialized_item):
                                enhanced_feature = ensure_map_compatible_feature(serialized_item, len(serialized_features))
                                if enhanced_feature:
                                    serialized_features.append(enhanced_feature)
                                        
                    except Exception as e:
                        print(f"❌ Error processing log feature: {e}")
                        continue
                
                if serialized_features:
                    print(f"✅ Returning geographic data from logs: {len(serialized_features)} features")
                    
                    current_map_state["features"] = serialized_features
                    current_map_state["last_updated"] = datetime.now().isoformat()
                    
                    return jsonify({
                        "response": description_text or "AI completed flexible spatial analysis.",
                        "geojson_data": serialized_features,
                        "agent_type": "ai_flexible_geographic_processed",
                        "ai_method": "flexible_analysis",
                        "tools_used": "ai_choice"
                    })
        
        # Default: return whatever the AI said
        print(f"💬 Returning flexible AI text response (no geographic data found)")
        print(f"   Response content: {str(result_text)[:200]}...")
        return jsonify({
            "response": str(result_text),
            "agent_type": "ai_flexible_text",
            "ai_method": "flexible_analysis",
            "tools_used": "ai_choice"
        })
        
    except Exception as e:
        error_msg = f"Flexible AI error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({
            "error": error_msg,
            "agent_type": "error",
            "tools_used": "none"
        })

    finally:
        print("🎉 FLEXIBLE AI QUERY COMPLETED")
        print("="*80 + "\n")


def extract_and_process_geographic_data(structured_response):
    """Extract and process geographic data from AI response."""
    data_fields = ['geojson_data', 'features', 'data', 'results', 'spatial_data']
    
    for data_field in data_fields:
        if data_field in structured_response:
            potential_data = structured_response[data_field]
            print(f"🔍 Checking data field '{data_field}': {type(potential_data)}")
            
            # Try to process as GeoJSON (FeatureCollection or array)
            processed_features = process_geojson_response(potential_data)
            if processed_features and len(processed_features) > 0:
                print(f"✅ Successfully processed {len(processed_features)} features from {data_field}")
                return processed_features
            
            # Fallback: try existing logic for direct feature arrays
            if isinstance(potential_data, list) and len(potential_data) > 0:
                first_item = potential_data[0]
                if isinstance(first_item, dict):
                    has_geographic_fields = any(geo_field in first_item for geo_field in ['lat', 'lon', 'geometry', 'coordinates'])
                    if has_geographic_fields:
                        print(f"✅ Found legacy geographic data in field: {data_field}")
                        return potential_data
    
    return None


def process_geojson_response(data):
    """Process GeoJSON data from AI response and convert to frontend format."""
    try:
        print(f"🔍 Processing GeoJSON response: {type(data)}")
        
        # Handle FeatureCollection format
        if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
            print("✅ Found GeoJSON FeatureCollection")
            features = data.get('features', [])
            print(f"   Features in collection: {len(features)}")
            
            processed_features = []
            for i, feature in enumerate(features):
                try:
                    # Convert GeoJSON feature to frontend format
                    processed_feature = convert_geojson_feature_to_frontend(feature, i)
                    if processed_feature:
                        processed_features.append(processed_feature)
                        print(f"   ✅ Feature {i+1} processed successfully")
                    else:
                        print(f"   ❌ Feature {i+1} failed processing")
                except Exception as e:
                    print(f"   ❌ Error processing feature {i+1}: {e}")
                    
            return processed_features
        
        # Handle direct array of features
        elif isinstance(data, list):
            print("✅ Found direct array of features")
            processed_features = []
            for i, feature in enumerate(data):
                processed_feature = convert_geojson_feature_to_frontend(feature, i)
                if processed_feature:
                    processed_features.append(processed_feature)
            return processed_features
            
        else:
            print(f"❌ Unrecognized GeoJSON format: {type(data)}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing GeoJSON: {e}")
        return None


def convert_geojson_feature_to_frontend(geojson_feature, index):
    """Convert a single GeoJSON feature to frontend-compatible format."""
    try:
        if not isinstance(geojson_feature, dict):
            return None
            
        # Extract geometry
        geometry = geojson_feature.get('geometry', {})
        if not geometry:
            return None
            
        # Calculate centroid for lat/lon
        centroid = calculate_centroid_from_geojson_geometry(geometry)
        if not centroid:
            return None
            
        lat, lon = centroid
        
        # Extract properties
        properties = geojson_feature.get('properties', {})
        
        # Create a meaningful name
        building_id = properties.get('id', f'Building-{index+1}')
        name = f"Building {building_id[-6:]}" if len(str(building_id)) > 6 else str(building_id)
        
        # Create description
        desc_parts = []
        if properties.get('bouwjaar'):
            desc_parts.append(f"Built: {properties['bouwjaar']}")
        if properties.get('oppervlakte') and properties['oppervlakte'] > 0:
            desc_parts.append(f"Area: {properties['oppervlakte']}m²")
        if properties.get('gebruiksdoel'):
            desc_parts.append(f"Use: {properties['gebruiksdoel']}")
            
        description = " | ".join(desc_parts) if desc_parts else "Building feature"
        
        # Create frontend-compatible feature
        frontend_feature = {
            'type': 'Feature',
            'name': name,
            'lat': lat,
            'lon': lon,
            'description': description,
            'geometry': geometry,
            'properties': {
                **properties,
                'area_m2': properties.get('oppervlakte', 0)  # Normalize area field
            }
        }
        
        return frontend_feature
        
    except Exception as e:
        print(f"❌ Error converting feature {index}: {e}")
        return None


def calculate_centroid_from_geojson_geometry(geometry):
    """Calculate centroid from GeoJSON geometry."""
    try:
        if not geometry or 'type' not in geometry or 'coordinates' not in geometry:
            return None
        
        geom_type = geometry['type']
        coordinates = geometry['coordinates']
        
        if geom_type == 'Point':
            # For point, coordinates are [lon, lat]
            return [coordinates[1], coordinates[0]]  # Return [lat, lon]
        
        elif geom_type == 'Polygon':
            # For polygon, take centroid of exterior ring
            if coordinates and len(coordinates) > 0:
                exterior_ring = coordinates[0]
                if len(exterior_ring) > 0:
                    # Calculate average of all points
                    avg_lon = sum(coord[0] for coord in exterior_ring) / len(exterior_ring)
                    avg_lat = sum(coord[1] for coord in exterior_ring) / len(exterior_ring)
                    return [avg_lat, avg_lon]  # Return [lat, lon]
        
        elif geom_type == 'LineString':
            # For linestring, use midpoint
            if coordinates and len(coordinates) > 0:
                mid_idx = len(coordinates) // 2
                coord = coordinates[mid_idx]
                return [coord[1], coord[0]]  # Return [lat, lon]
        
        return None
        
    except Exception as e:
        print(f"Error calculating centroid: {e}")
        return None

def ensure_map_compatible_feature(feature, index):
    """Ensure feature has all required fields for frontend map display"""
    try:
        # Create a copy to avoid modifying original
        enhanced_feature = feature.copy()
        
        # Ensure 'type' field
        if 'type' not in enhanced_feature:
            enhanced_feature['type'] = 'Feature'
        
        # Ensure 'name' field
        if 'name' not in enhanced_feature:
            # Try to create a meaningful name
            properties = enhanced_feature.get('properties', {})
            identificatie = properties.get('identificatie', f'Feature-{index+1}')
            enhanced_feature['name'] = f"Building {identificatie[-6:]}" if len(str(identificatie)) > 6 else str(identificatie)
        
        # Ensure 'lat' and 'lon' fields
        if 'lat' not in enhanced_feature or 'lon' not in enhanced_feature:
            # Try to extract from geometry
            geometry = enhanced_feature.get('geometry', {})
            centroid = calculate_centroid_from_geometry(geometry)
            if centroid:
                enhanced_feature['lat'] = centroid[0]
                enhanced_feature['lon'] = centroid[1]
            else:
                print(f"⚠️ Feature {index} missing coordinates and couldn't calculate from geometry")
                return None
        
        # Validate coordinates are in Netherlands
        lat = enhanced_feature.get('lat', 0)
        lon = enhanced_feature.get('lon', 0)
        if not (50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0):
            print(f"⚠️ Feature {index} coordinates outside Netherlands: {lat}, {lon}")
            return None
        
        # Ensure 'description' field
        if 'description' not in enhanced_feature:
            # Create description from properties
            properties = enhanced_feature.get('properties', {})
            desc_parts = []
            
            # Add building info if available
            if 'bouwjaar' in properties:
                desc_parts.append(f"Built: {properties['bouwjaar']}")
            
            # Add area if available
            area_fields = ['oppervlakte', 'oppervlakte_min', 'oppervlakte_max', 'area']
            for area_field in area_fields:
                if area_field in properties and properties[area_field]:
                    area = properties[area_field]
                    desc_parts.append(f"Area: {area}m²")
                    break
            
            enhanced_feature['description'] = " | ".join(desc_parts) if desc_parts else "Building feature"
        
        # Ensure 'geometry' field is valid
        if 'geometry' not in enhanced_feature or not enhanced_feature['geometry']:
            # Create point geometry from lat/lon
            enhanced_feature['geometry'] = {
                'type': 'Point',
                'coordinates': [lon, lat]
            }
        else:
            # Validate existing geometry
            geometry = enhanced_feature['geometry']
            if not validate_and_fix_geometry(geometry):
                # Fallback to point geometry
                enhanced_feature['geometry'] = {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                }
        
        # Ensure 'properties' field
        if 'properties' not in enhanced_feature:
            enhanced_feature['properties'] = {}
        
        # Make sure everything is JSON serializable
        enhanced_feature = ensure_json_serializable(enhanced_feature)
        
        return enhanced_feature
        
    except Exception as e:
        print(f"❌ Error enhancing feature {index}: {e}")
        return None


def calculate_centroid_from_geometry(geometry):
    """Calculate centroid from geometry object"""
    try:
        if not geometry or 'type' not in geometry or 'coordinates' not in geometry:
            return None
        
        geom_type = geometry['type']
        coordinates = geometry['coordinates']
        
        if geom_type == 'Point':
            # For point, coordinates are [lon, lat]
            return [coordinates[1], coordinates[0]]  # Return [lat, lon]
        
        elif geom_type == 'Polygon':
            # For polygon, take centroid of exterior ring
            if coordinates and len(coordinates) > 0:
                exterior_ring = coordinates[0]
                if len(exterior_ring) > 0:
                    # Calculate average of all points
                    avg_lon = sum(coord[0] for coord in exterior_ring) / len(exterior_ring)
                    avg_lat = sum(coord[1] for coord in exterior_ring) / len(exterior_ring)
                    return [avg_lat, avg_lon]  # Return [lat, lon]
        
        return None
        
    except Exception as e:
        print(f"Error calculating centroid: {e}")
        return None


# FIXED: Helper functions that were missing
def _extract_geographic_data_flexible(data_dict):
    """Flexibly extract geographic data from any tool result."""
    geographic_data = None
    description = None
    
    # Look for various patterns the AI might use
    potential_geo_fields = [
        'geojson_data', 'features', 'data', 'results', 'spatial_data', 
        'buildings', 'parcels', 'locations', 'points', 'polygons'
    ]
    
    potential_desc_fields = [
        'text_description', 'description', 'summary', 'message', 
        'response', 'analysis', 'explanation'
    ]
    
    # Extract geographic data
    for field in potential_geo_fields:
        if field in data_dict:
            potential_data = data_dict[field]
            if isinstance(potential_data, list) and len(potential_data) > 0:
                # Check if items look like geographic features
                first_item = potential_data[0]
                if isinstance(first_item, dict):
                    if _is_valid_geographic_feature(first_item):
                        geographic_data = potential_data
                        break
    
    # Extract description
    for field in potential_desc_fields:
        if field in data_dict:
            description = data_dict[field]
            break
    
    return geographic_data, description


def _is_valid_geographic_feature(feature_dict):
    """Check if a dictionary looks like a valid geographic feature."""
    if not isinstance(feature_dict, dict):
        return False
    
    # Must have coordinates or geometry
    has_coordinates = ('lat' in feature_dict and 'lon' in feature_dict)
    has_geometry = 'geometry' in feature_dict
    
    if not (has_coordinates or has_geometry):
        return False
    
    # If has coordinates, they should be reasonable for Netherlands
    if has_coordinates:
        lat = feature_dict.get('lat', 0)
        lon = feature_dict.get('lon', 0)
        
        # Basic Netherlands bounds check
        if not (50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0):
            return False
    
    return True


def _extract_geographic_data_flexible(data_dict):
    """Flexibly extract geographic data from any tool result."""
    geographic_data = None
    description = None
    
    # Look for various patterns the AI might use
    potential_geo_fields = [
        'geojson_data', 'features', 'data', 'results', 'spatial_data', 
        'buildings', 'parcels', 'locations', 'points', 'polygons'
    ]
    
    potential_desc_fields = [
        'text_description', 'description', 'summary', 'message', 
        'response', 'analysis', 'explanation'
    ]
    
    # Extract geographic data
    for field in potential_geo_fields:
        if field in data_dict:
            potential_data = data_dict[field]
            if isinstance(potential_data, list) and len(potential_data) > 0:
                # Check if items look like geographic features
                first_item = potential_data[0]
                if isinstance(first_item, dict):
                    if _is_valid_geographic_feature(first_item):
                        geographic_data = potential_data
                        break
    
    # Extract description
    for field in potential_desc_fields:
        if field in data_dict:
            description = data_dict[field]
            break
    
    return geographic_data, description


def _is_valid_geographic_feature(feature_dict):
    """Check if a dictionary looks like a valid geographic feature."""
    if not isinstance(feature_dict, dict):
        return False
    
    # Must have coordinates or geometry
    has_coordinates = ('lat' in feature_dict and 'lon' in feature_dict)
    has_geometry = 'geometry' in feature_dict
    
    if not (has_coordinates or has_geometry):
        return False
    
    # If has coordinates, they should be reasonable for Netherlands
    if has_coordinates:
        lat = feature_dict.get('lat', 0)
        lon = feature_dict.get('lon', 0)
        
        # Basic Netherlands bounds check
        if not (50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0):
            return False
    
    return True




def debug_geojson_format(features):
    """Debug function to inspect GeoJSON data format"""
    print("\n=== GEOJSON DEBUG ===")
    print(f"Number of features: {len(features)}")
    
    if features:
        first_feature = features[0]
        print(f"First feature type: {type(first_feature)}")
        print(f"First feature keys: {list(first_feature.keys()) if isinstance(first_feature, dict) else 'Not a dict'}")
        
        # Check required fields for your frontend
        required_fields = ['type', 'name', 'lat', 'lon', 'description', 'geometry', 'properties']
        missing_fields = []
        
        for field in required_fields:
            if field not in first_feature:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
        else:
            print("✅ All required fields present")
        
        # Check coordinate values
        if 'lat' in first_feature and 'lon' in first_feature:
            lat = first_feature['lat']
            lon = first_feature['lon']
            print(f"Coordinates: lat={lat}, lon={lon}")
            
            # Check if coordinates are reasonable for Netherlands
            if not (50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0):
                print(f"⚠️ Coordinates outside Netherlands bounds")
        
        # Check geometry format
        if 'geometry' in first_feature:
            geom = first_feature['geometry']
            print(f"Geometry type: {geom.get('type', 'Unknown')}")
            if 'coordinates' in geom:
                coords = geom['coordinates']
                print(f"Geometry coordinates sample: {str(coords)[:100]}...")
        
        # Print full first feature (truncated)
        print(f"Sample feature: {str(first_feature)[:500]}...")
    
    print("===================\n")



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