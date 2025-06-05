# app.py - Simple Intelligent PDOK Application

import os
import json
import yaml
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

# Initialize OpenAI model
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base="https://api.openai.com/v1",
    api_key=os.getenv('OPENAI_API_KEY'),
    max_completion_tokens=3072,  # Smaller for faster responses
)

# Global state
current_map_state = {
    "features": [],
    "search_location": None,
    "layer_type": None,
    "last_query": None
}

def load_simple_system_prompt() -> dict:
    """Load the system prompt from YAML file."""
    try:
        # Try to load from YAML file first
        with open('static/pdok_spatial_prompt_template.yml', 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            print("✅ Loaded system prompt from pdok_spatial_prompt_template.yml")
            return config
    except FileNotFoundError:
        print("⚠️ pdok_spatial_prompt_template.yml not found, using embedded prompt")
        # Fallback to embedded prompt if file doesn't exist
        return {
            "system_prompt": """You are an intelligent PDOK spatial analysis assistant specializing in Dutch geospatial data.

            **🧠 CORE INTELLIGENCE:**
            - Understand spatial data needs from natural language queries
            - Extract locations intelligently (addresses, cities, postal codes, landmarks)
            - Choose appropriate PDOK services based on user intent
            - Provide meaningful spatial insights

            **⚡ EFFICIENCY PRINCIPLE:**
            Maximum 3 tool calls to complete any task. Trust your intelligence and the tool docstrings.

            **🎯 AVAILABLE PDOK DATA:**
            - **bestandbodemgebruik**: Land use, agricultural data
            - **bag**: Buildings, construction years, addresses  
            - **cadastral**: Property parcels, development potential
            - **natura2000**: Protected nature areas, conservation
            - **cbs**: Administrative boundaries, municipalities

            **📍 LOCATION HANDLING:**
            When users mention locations, always extract and use the most specific reference available. Handle implicit location references intelligently.

            **🚀 WORKFLOW:**
            1. **Understand** the query naturally
            2. **Locate** coordinates if mentioned using find_location_coordinates()
            3. **Discover** appropriate service using discover_pdok_services()
            4. **Fetch** spatial data using fetch_pdok_data()
            5. **Respond** with final_answer() in proper Python code format

            **CRITICAL OUTPUT FORMAT - MUST FOLLOW EXACTLY:**

            You MUST end every response with Python code that calls final_answer(). 
            NEVER return raw JSON. Always use this exact pattern:

            Thoughts: Brief analysis of what I found
            Code:
            ```py
            import json

            # Process the data from tools
            features = result.get('features', [])  # Use actual data from fetch_pdok_data()

            # Create response
            response_data = {
                "text_description": "Found X features near Y location",
                "geojson_data": features,
                "search_location": location_coords,
                "layer_type": "service_name"
            }

            final_answer(json.dumps(response_data))
            ```<end_code>

            **VALIDATION RULES:**
            - geojson_data MUST contain the actual features array from fetch_pdok_data()
            - search_location MUST contain the coordinates from find_location_coordinates()
            - text_description MUST summarize what was actually found
            - layer_type MUST match the service used

            Use the tool docstrings to understand proper usage. Always return real data, never mock or simulate.""",

                        "planning": {
                            "initial_plan": """1. **Parse Query**: Extract user intent and any locations mentioned
            2. **Get Coordinates**: Use find_location_coordinates() if location mentioned
            3. **Select Service**: Choose appropriate PDOK service based on data type needed
            4. **Fetch Data**: Use fetch_pdok_data() to get actual spatial features
            5. **Format Response**: Use final_answer() with proper Python code format""",

                            "update_plan_pre_messages": "Update your approach based on tool results. Ensure you end with proper final_answer() format.",

                            "update_plan_post_messages": "Revise your plan. Remember: MUST end with Python code calling final_answer(json.dumps(...))"
                        },

                        "managed_agent": {
                            "task": """Spatial Analysis Request: {{task}}

            Use available tools to get real PDOK data. End with final_answer() in Python code format.""",

                            "report": "Spatial analysis completed: {{final_answer}}"
                        },

                        "final_answer": {
                            "pre_messages": """Provide response using final_answer() function with proper Python code format.
            NEVER return raw JSON - always wrap in final_answer(json.dumps(...))""",

                            "post_messages": """User Query: {{task}}

            REQUIRED FORMAT:
            Thoughts: Your analysis
            Code:
            ```py
            import json
            final_answer(json.dumps({"text_description": "...", "geojson_data": [...], "search_location": {...}, "layer_type": "..."}))
            ```<end_code>"""
            }
        }
    except Exception as e:
        print(f"❌ Error loading system prompt: {e}")
        # Minimal fallback
        return {
            "system_prompt": "You are a PDOK spatial analysis assistant. Always end with final_answer(json.dumps(...)) in Python code format.",
            "planning": {"initial_plan": "Use tools to help with spatial analysis"},
            "managed_agent": {"task": "{{task}}", "report": "{{final_answer}}"},
            "final_answer": {"pre_messages": "Use final_answer() format", "post_messages": "End with Python code"}
        }

@tool
def analyze_current_map_features() -> dict:
    """Analyze current map features."""
    global current_map_state
    features = current_map_state.get("features", [])
    
    if not features:
        return {"message": "No features currently displayed", "feature_count": 0}
    
    return {
        "feature_count": len(features),
        "layer_type": current_map_state.get("layer_type", "unknown"),
        "summary": f"Currently displaying {len(features)} features"
    }

def create_simple_agent():
    """Create agent with simple, essential tools."""
    
    try:
        # Import essential tools only
        from tools.enhanced_pdok_location_tool import IntelligentLocationSearchTool
        from tools.enhanced_discovery_tool import IntentDrivenPDOKDiscoveryTool
        from tools.flexible_ai_driven_spatial_tools import FlexibleSpatialDataTool
        
        tools = [
            IntelligentLocationSearchTool(),    # Location search
            IntentDrivenPDOKDiscoveryTool(),    # Service discovery
            FlexibleSpatialDataTool(),          # Data fetching
            analyze_current_map_features        # Map analysis
        ]
        
        print("✅ Essential tools loaded")
        tools_available = True
        
    except ImportError as e:
        print(f"❌ Could not import tools: {e}")
        tools = [analyze_current_map_features]
        tools_available = False
    
    print(f"🧠 Creating SIMPLE intelligent agent with {len(tools)} tools")
    
    # Load simple system prompt
    prompt_config = load_simple_system_prompt()
    
    # Create agent
    agent = CodeAgent(
        model=model,
        tools=tools,
        max_steps=10,  # Keep it simple
        prompt_templates=prompt_config,
        additional_authorized_imports=["json", "re","geopy"]
    )
    
    return agent, tools_available

# Initialize the simple agent
agent, tools_available = create_simple_agent()

def create_flexible_legend_data(features, layer_type):
    """Create simple legend data."""
    if not features or len(features) == 0:
        return None
    
    legend_data = {
        "layer_type": layer_type,
        "title": f"📊 {layer_type.replace('_', ' ').title()} Features",
        "categories": [
            {"label": f"{layer_type.replace('_', ' ').title()}", "color": "#3b82f6", "count": len(features)}
        ],
        "statistics": {
            "total_features": len(features)
        }
    }
    
    return legend_data

def extract_search_location_from_response(response_text, features):
    """Extract search location as fallback."""
    if features and len(features) > 0:
        lats = [f.get('lat', 0) for f in features if f.get('lat')]
        lons = [f.get('lon', 0) for f in features if f.get('lon')]
        
        if lats and lons:
            return {
                "lat": sum(lats) / len(lats),
                "lon": sum(lons) / len(lons),
                "name": "Search Area",
                "source": "feature_centroid"
            }
    
    return None

# Flask routes
@app.route('/')
def index():
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle queries with simple intelligence."""
    global current_map_state
    
    print("\n" + "="*50)
    print("🧠 SIMPLE INTELLIGENT PROCESSING")
    print("="*50)
    
    data = request.json
    query_text = data.get('query', '')
    
    print(f"Query: {query_text}")
    current_map_state["last_query"] = query_text
    
    try:
        print("🚀 Running simple intelligent agent...")
        
        # Use the loaded system prompt
        prompt_config = load_simple_system_prompt()
        system_prompt = prompt_config["system_prompt"].format(task=query_text)
        
        result = agent.run(system_prompt)
        
        print(f"Agent completed processing")
        
        # Process response
        if isinstance(result, dict):
            structured_response = result
        else:
            result_text = str(result)
            print(f"🔍 Processing agent result...")
            
            try:
                if result_text.strip().startswith('{') and result_text.strip().endswith('}'):
                    structured_response = json.loads(result_text.strip())
                    print(f"✅ Parsed clean JSON directly")
                else:
                    import re
                    json_pattern = r'\{[^{}]*?"text_description"[^{}]*?"geojson_data".*?\}'
                    json_match = re.search(json_pattern, result_text, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(0)
                        structured_response = json.loads(json_str)
                        print(f"✅ Extracted JSON from response")
                    else:
                        structured_response = {"text_description": result_text}
                        print(f"⚠️ No JSON found, treating as text response")
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                structured_response = {"text_description": result_text}
            except Exception as e:
                print(f"❌ Response processing error: {e}")
                structured_response = {"text_description": result_text}
        
        # Extract components
        response_text = structured_response.get('text_description', 'Analysis completed')
        geojson_data = structured_response.get('geojson_data', [])
        search_location = structured_response.get('search_location')
        layer_type = structured_response.get('layer_type', 'features')
        
        # Validate features
        valid_features = []
        if isinstance(geojson_data, list):
            print(f"🔍 Validating {len(geojson_data)} features...")
            
            for i, feature in enumerate(geojson_data):
                if isinstance(feature, dict):
                    has_coords = ('lat' in feature and 'lon' in feature and
                                  feature.get('lat') != 0 and feature.get('lon') != 0)
                    has_geometry = 'geometry' in feature
                    
                    if has_coords and has_geometry:
                        lat, lon = feature['lat'], feature['lon']
                        if 50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0:
                            valid_features.append(feature)
                        else:
                            print(f"   ⚠️ Feature {i+1}: coordinates outside Netherlands bounds: {lat}, {lon}")
                    else:
                        missing = []
                        if not has_coords:
                            missing.append("lat/lon")
                        if not has_geometry:
                            missing.append("geometry")
                        print(f"   ⚠️ Feature {i+1}: missing {', '.join(missing)}")
                else:
                    print(f"   ⚠️ Feature {i+1}: not a dictionary object")
        
        print(f"✅ Validated {len(valid_features)}/{len(geojson_data) if isinstance(geojson_data, list) else 0} features")
        
        # Update state
        current_map_state["features"] = valid_features
        current_map_state["layer_type"] = layer_type
        current_map_state["search_location"] = search_location
        
        # Create legend
        legend_data = None
        if valid_features:
            legend_data = create_flexible_legend_data(valid_features, layer_type)
        
        # Fallback location
        if not search_location and valid_features:
            search_location = extract_search_location_from_response(response_text, valid_features)
            current_map_state["search_location"] = search_location
        
        return jsonify({
            "response": response_text,
            "geojson_data": valid_features,
            "search_location": search_location,
            "layer_type": layer_type,
            "legend_data": legend_data,
            "agent_type": "simple_intelligent"
        })
        
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "error": error_msg,
            "response": "I encountered an error. Please try a simpler query.",
            "agent_type": "error"
        })
    
    finally:
        print("🎉 SIMPLE PROCESSING COMPLETED")
        print("="*50 + "\n")
@app.route('/api/map-state', methods=['GET'])
def get_map_state():
    """Get current map state."""
    return jsonify(current_map_state)

@app.route('/api/clear-map', methods=['POST'])
def clear_map():
    """Clear map."""
    global current_map_state
    current_map_state = {
        "features": [],
        "search_location": None,
        "layer_type": None,
        "last_query": None
    }
    return jsonify({"success": True})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_available": tools_available,
        "agent_ready": agent is not None
    })

if __name__ == '__main__':
    print("🚀 Starting SIMPLE Intelligent PDOK Application")
    print("="*40)
    print("🧠 FEATURES:")
    print("  ✅ Natural AI intelligence (no complex analyzers)")
    print("  ✅ Simple 3-step workflow")
    print("  ✅ Always plots locations")
    print("  ✅ Always shows data")
    print("  ✅ Fast responses")
    
    print("\\n🎯 TRUST THE AI:")
    print("  🧠 AI understands queries naturally")
    print("  📍 AI extracts locations intelligently") 
    print("  🎯 AI chooses right services")
    print("  ⚡ AI provides quick insights")
    
    print("\\nTEST QUERIES:")
    print("  'Show agricultural land in Utrecht'")
    print("  'Buildings near Amsterdam station'")
    print("  'Large parcels in Groningen'")
    
    print(f"\\n🌐 http://localhost:5000")
    print("="*40)
    
    app.run(debug=True, port=5000, host='0.0.0.0')