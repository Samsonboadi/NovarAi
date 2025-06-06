
import os
import json
import yaml
import traceback
import re
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

# Initialize OpenAI model
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base="https://api.openai.com/v1",
    api_key=os.getenv('OPENAI_API_KEY'),
    max_completion_tokens=3072,
)

# Global state
current_map_state = {
    "features": [],
    "search_location": None,
    "layer_type": None,
    "last_query": None
}

def load_prompt_templates():
    """Load prompt templates using smolagents pattern."""
    yaml_paths = [
        'static/pdok_spatial_prompt_template.yml',
        'pdok_spatial_prompt_template.yml',
        'prompts.yaml',
        os.path.join(os.path.dirname(__file__), 'static', 'pdok_spatial_prompt_template.yml')
    ]
    
    for yaml_path in yaml_paths:
        try:
            if os.path.exists(yaml_path):
                print(f"📂 Loading: {yaml_path}")
                with open(yaml_path, 'r', encoding='utf-8') as stream:
                    prompt_templates = yaml.safe_load(stream)
                if prompt_templates and isinstance(prompt_templates, dict):
                    print(f"✅ Loaded prompt templates from {yaml_path}")
                    print(f"📋 Sections: {list(prompt_templates.keys())}")
                    return prompt_templates
                print(f"⚠️ Invalid YAML structure in {yaml_path}")
        except Exception as e:
            print(f"❌ Error loading {yaml_path}: {e}")
    
    print("⚠️ No valid YAML found, using fallback")
    return get_fallback_prompt_templates()

def get_fallback_prompt_templates():
    """Fallback prompt templates for smolagents."""
    return {
        "system_prompt": """You are an expert PDOK spatial analysis assistant for Dutch geospatial data.

CRITICAL TOOL USAGE:
```python
# Step 1: Find location
location = find_location_coordinates("location_name")

# Step 2: Discover service
service_info = discover_pdok_services("bag", get_attributes=True)
service_url = service_info["service"]["url"]
layer_name = service_info["service"]["primary_layer"]

# Step 3: Fetch data
search_area = {"center": [location["lat"], location["lon"]], "radius_km": 1.0}
result = fetch_pdok_data(
    service_url=service_url,
    layer_name=layer_name,
    search_area=search_area,
    filters={},
    max_features=50,
    purpose="Analysis"
)

# Step 4: Return results
import json
final_answer(json.dumps({
    "text_description": f"Found {len(result['features'])} features near {location['name']}",
    "geojson_data": result["features"],
    "search_location": location,
    "layer_type": "bag"
}))
```

RULES:
1. Always call discover_pdok_services() first
2. Never use shortcut URLs
3. Use search_area: {"center": [lat, lon], "radius_km": float}
4. End with final_answer(json.dumps({...}))

SERVICE MAPPING:
- Buildings → "bag"
- Land use → "bestandbodemgebruik"
- Parcels → "cadastral"
- Nature → "natura2000"
""",
        "planning": {
            "initial_plan": "1. Find location 2. Discover PDOK service 3. Fetch data 4. Format response",
            "update_plan_pre_messages": "Review results and adjust",
            "update_plan_post_messages": "End with final_answer"
        },
        "managed_agent": {
            "task": "{{task}}",
            "report": "{{final_answer}}"
        },
        "final_answer": {
            "pre_messages": "Use final_answer with JSON",
            "post_messages": "Required: final_answer(json.dumps({\"text_description\": \"...\", \"geojson_data\": [...], \"search_location\": {...}, \"layer_type\": \"...\"}))"
        }
    }

@tool
def analyze_current_map_features() -> dict:
    """Analyze current map features."""
    global current_map_state
    features = current_map_state.get("features", [])
    return {
        "feature_count": len(features),
        "layer_type": current_map_state.get("layer_type", "unknown"),
        "summary": f"Displaying {len(features)} features"
    } if features else {"message": "No features displayed", "feature_count": 0}

def create_intelligent_agent():
    """Create agent with smolagents pattern."""
    try:
        from tools.enhanced_pdok_location_tool import IntelligentLocationSearchTool
        from tools.enhanced_discovery_tool import IntentDrivenPDOKDiscoveryTool
        from tools.flexible_ai_driven_spatial_tools import FlexibleSpatialDataTool
        tools = [
            IntelligentLocationSearchTool(),
            IntentDrivenPDOKDiscoveryTool(),
            FlexibleSpatialDataTool(),
            analyze_current_map_features
        ]
        print("✅ Tools loaded")
        tools_available = True
    except ImportError as e:
        print(f"❌ Tool import error: {e}")
        tools = [analyze_current_map_features]
        tools_available = False
    
    print(f"🧠 Creating agent with {len(tools)} tools")
    prompt_templates = load_prompt_templates()
    print(f"📋 Prompt sections: {list(prompt_templates.keys())}")
    
    agent = CodeAgent(
        model=model,
        tools=tools,
        max_steps=8,
        verbosity_level=1,
        grammar=None,
        planning_interval=None,
        name=None,
        description=None,
        prompt_templates=prompt_templates,
        additional_authorized_imports=["json", "re", "geopy", "math"]
    )
    return agent, tools_available

# Initialize agent
agent, tools_available = create_intelligent_agent()

def safe_json_parse(text: str) -> dict:
    """Enhanced JSON parsing with fallbacks."""
    debug_info = {"original_length": len(text), "parsing_attempts": []}
    
    # Method 1: Direct JSON
    try:
        if text.strip().startswith('{') and text.strip().endswith('}'):
            parsed = json.loads(text.strip())
            debug_info["parsing_attempts"].append({"method": "direct_json", "success": True})
            return parsed
    except json.JSONDecodeError as e:
        debug_info["parsing_attempts"].append({"method": "direct_json", "success": False, "error": str(e)})
    
    # Method 2: Extract from final_answer
    try:
        match = re.search(r'final_answer\s*\(\s*json\.dumps\s*\(\s*(\{.*?\})\s*\)\s*\)', text, re.DOTALL)
        if match:
            json_str = match.group(1).replace('\n', '').replace('  ', ' ')
            parsed = json.loads(json_str)
            debug_info["parsing_attempts"].append({"method": "final_answer", "success": True})
            return parsed
    except (json.JSONDecodeError, AttributeError) as e:
        debug_info["parsing_attempts"].append({"method": "final_answer", "success": False, "error": str(e)})
    
    # Method 3: Reconstruct components
    try:
        components = {}
        text_match = re.search(r'"text_description"\s*:\s*"([^"]*)"', text)
        if text_match:
            components["text_description"] = text_match.group(1)
        
        geojson_match = re.search(r'"geojson_data"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if geojson_match:
            try:
                components["geojson_data"] = json.loads(geojson_match.group(1))
            except:
                components["geojson_data"] = []
        
        location_match = re.search(r'"search_location"\s*:\s*(\{[^}]*\})', text)
        if location_match:
            try:
                components["search_location"] = json.loads(location_match.group(1))
            except:
                components["search_location"] = None
        
        layer_match = re.search(r'"layer_type"\s*:\s*"([^"]*)"', text)
        if layer_match:
            components["layer_type"] = layer_match.group(1)
        
        if components:
            reconstructed = {
                "text_description": components.get("text_description", "Analysis completed"),
                "geojson_data": components.get("geojson_data", []),
                "search_location": components.get("search_location"),
                "layer_type": components.get("layer_type", "unknown")
            }
            debug_info["parsing_attempts"].append({"method": "reconstruction", "success": True})
            return reconstructed
    except Exception as e:
        debug_info["parsing_attempts"].append({"method": "reconstruction", "success": False, "error": str(e)})
    
    debug_info["parsing_attempts"].append({"method": "fallback", "success": True})
    return {
        "text_description": f"Could not parse response. Raw: {text[:200]}...",
        "geojson_data": [],
        "search_location": None,
        "layer_type": "error"
    }

def validate_and_fix_features(features, search_location=None, radius_km=15):
    """Validate and fix feature data with strict radius filtering."""
    if not isinstance(features, list):
        print("⚠️ Features is not a list")
        return []
    
    valid_features = []
    
    for i, feature in enumerate(features):
        try:
            if not isinstance(feature, dict):
                print(f"   ⚠️ Feature {i+1}: not a dictionary")
                continue
            
            has_geometry = 'geometry' in feature and feature['geometry'] is not None
            if not has_geometry:
                print(f"   ❌ Feature {i+1}: missing or invalid geometry")
                continue
            
            geometry = feature['geometry']
            lat, lon = None, None
            
            if geometry.get('type') == 'Polygon' and 'coordinates' in geometry:
                coords = geometry['coordinates'][0]
                if coords and len(coords) > 0:
                    lons = [coord[0] for coord in coords if len(coord) >= 2]
                    lats = [coord[1] for coord in coords if len(coord) >= 2]
                    if lons and lats:
                        lon = sum(lons) / len(lons)
                        lat = sum(lats) / len(lats)
                        feature['lat'] = lat
                        feature['lon'] = lon
                    else:
                        print(f"   ❌ Feature {i+1}: invalid polygon coordinates")
                        continue
            elif geometry.get('type') == 'Point' and 'coordinates' in geometry:
                coords = geometry['coordinates']
                if len(coords) >= 2:
                    lon = coords[0]
                    lat = coords[1]
                    feature['lat'] = lat
                    feature['lon'] = lon
                else:
                    print(f"   ❌ Feature {i+1}: invalid point coordinates")
                    continue
            else:
                print(f"   ⚠️ Feature {i+1}: unsupported geometry type: {geometry.get('type')}")
                continue
            
            # Validate Netherlands bounds
            if not (50.0 <= lat <= 54.0 and 3.0 <= lon <= 8.0):
                print(f"   ❌ Feature {i+1}: coordinates outside Netherlands bounds: {lat}, {lon}")
                continue
            
            # Radius validation
            if search_location and 'lat' in search_location and 'lon' in search_location:
                R = 6371  # Earth's radius in km
                lat1, lon1 = radians(search_location['lat']), radians(search_location['lon'])
                lat2, lon2 = radians(lat), radians(lon)
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                if distance > radius_km:
                    print(f"   ❌ Feature {i+1}: outside radius ({distance:.2f} km > {radius_km} km)")
                    continue
            
            # Ensure required fields
            if 'name' not in feature:
                feature['name'] = (feature.get('properties', {}).get('identificatie') or 
                                 feature.get('properties', {}).get('perceelnummer', f"Feature {i+1}"))
            
            if 'description' not in feature:
                props = feature.get('properties', {})
                desc_parts = []
                if props.get('kadastraleGrootteWaarde'):
                    area_m2 = float(props['kadastraleGrootteWaarde'])
                    desc_parts.append(f"Area: {area_m2:.0f} m² ({(area_m2/10000):.2f} ha)")
                if props.get('perceelnummer'):
                    desc_parts.append(f"Parcel: {props['perceelnummer']}")
                if props.get('bouwjaar'):
                    desc_parts.append(f"Built: {props['bouwjaar']}")
                if props.get('oppervlakte'):
                    desc_parts.append(f"Area: {props['oppervlakte']}m²")
                if props.get('status'):
                    desc_parts.append(f"Status: {props['status']}")
                if props.get('bodemgebruik'):
                    desc_parts.append(f"Land Use: {props['bodemgebruik']}")
                feature['description'] = " | ".join(desc_parts) if desc_parts else "PDOK spatial feature"
            
            valid_features.append(feature)
            print(f"   ✅ Feature {i+1}: valid ({feature['name']})")
        
        except Exception as e:
            print(f"   ❌ Feature {i+1} validation error: {e}")
            continue
    
    return valid_features

def create_flexible_legend_data(features, layer_type):
    """Create enhanced legend data for all layer types."""
    if not features or len(features) == 0:
        return None
    
    legend_data = {
        "layer_type": layer_type,
        "title": f"📊 {layer_type.replace('_', ' ').title()} Features",
        "statistics": {
            "total_features": len(features),
            "data_source": "PDOK Netherlands"
        }
    }
    
    if layer_type == "bag":
        legend_data["description"] = "Building data from Dutch Buildings and Addresses Database"
        legend_data["categories"] = [
            {"label": "Historic (< 1900)", "color": "#8B0000", "count": sum(1 for f in features if f.get('properties', {}).get('bouwjaar', 0) and int(f['properties']['bouwjaar']) < 1900)},
            {"label": "Pre-war (1900-1949)", "color": "#FF4500", "count": sum(1 for f in features if f.get('properties', {}).get('bouwjaar', 0) and 1900 <= int(f['properties']['bouwjaar']) < 1950)},
            {"label": "Post-war (1950-1979)", "color": "#32CD32", "count": sum(1 for f in features if f.get('properties', {}).get('bouwjaar', 0) and 1950 <= int(f['properties']['bouwjaar']) < 1980)},
            {"label": "Late 20th C (1980-1999)", "color": "#1E90FF", "count": sum(1 for f in features if f.get('properties', {}).get('bouwjaar', 0) and 1980 <= int(f['properties']['bouwjaar']) < 2000)},
            {"label": "Modern (2000+)", "color": "#FF1493", "count": sum(1 for f in features if f.get('properties', {}).get('bouwjaar', 0) and int(f['properties']['bouwjaar']) >= 2000)},
            {"label": "Unknown Age", "color": "#808080", "count": sum(1 for f in features if not f.get('properties', {}).get('bouwjaar'))}
        ]
    elif layer_type == "cadastral":
        legend_data["description"] = "Cadastral parcel data from Dutch Land Registry"
        legend_data["categories"] = [
            {"label": "Large (>5 ha)", "color": "#dc2626", "count": sum(1 for f in features if f.get('properties', {}).get('kadastraleGrootteWaarde', 0) and float(f['properties']['kadastraleGrootteWaarde']) / 10000 > 5)},
            {"label": "Medium (1-5 ha)", "color": "#f97316", "count": sum(1 for f in features if f.get('properties', {}).get('kadastraleGrootteWaarde', 0) and 1 <= float(f['properties']['kadastraleGrootteWaarde']) / 10000 <= 5)},
            {"label": "Small (<1 ha)", "color": "#22c55e", "count": sum(1 for f in features if f.get('properties', {}).get('kadastraleGrootteWaarde', 0) and float(f['properties']['kadastraleGrootteWaarde']) / 10000 < 1)}
        ]
    elif layer_type == "bestandbodemgebruik":
        legend_data["description"] = "Land use data from CBS Netherlands"
        legend_data["categories"] = [
            {"label": "Agricultural", "color": "#22c55e", "count": sum(1 for f in features if f.get('properties', {}).get('bodemgebruik', '').lower().includes('agrarisch'))},
            {"label": "Built-up", "color": "#ef4444", "count": sum(1 for f in features if f.get('properties', {}).get('bodemgebruik', '').lower().includes('bebouwd'))},
            {"label": "Forest", "color": "#16a34a", "count": sum(1 for f in features if f.get('properties', {}).get('bodemgebruik', '').lower().includes('bos'))},
            {"label": "Water", "color": "#3b82f6", "count": sum(1 for f in features if f.get('properties', {}).get('bodemgebruik', '').lower().includes('water'))}
        ]
    elif layer_type == "natura2000":
        legend_data["description"] = "Protected areas from Natura 2000"
        legend_data["categories"] = [
            {"label": "Nature Reserve", "color": "#22c55e", "count": len(features)}
        ]
    else:
        legend_data["description"] = "Generic spatial features from PDOK"
        legend_data["categories"] = [
            {"label": "Features", "color": "#3b82f6", "count": len(features)}
        ]
    
    return legend_data

def extract_search_location_from_response(response_text, features):
    """Extract fallback search location from features."""
    try:
        if features and len(features) > 0:
            lats = []
            lons = []
            for feature in features:
                if 'lat' in feature and 'lon' in feature:
                    lat, lon = feature['lat'], feature['lon']
                    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                        lats.append(lat)
                        lons.append(lon)
                elif 'geometry' in feature and feature['geometry']:
                    geom = feature['geometry']
                    if geom.get('type') == 'Point' and 'coordinates' in geom:
                        coords = geom['coordinates']
                        if len(coords) >= 2:
                            lons.append(coords[0])
                            lats.append(coords[1])
                    elif geom.get('type') == 'Polygon' and 'coordinates' in geom:
                        coords = geom['coordinates'][0]
                        if coords:
                            ring_lons = [c[0] for c in coords if len(c) >= 2]
                            ring_lats = [c[1] for c in coords if len(c) >= 2]
                            if ring_lons and ring_lats:
                                lons.append(sum(ring_lons) / len(ring_lons))
                                lats.append(sum(ring_lats) / len(ring_lats))
            if lats and lons:
                return {
                    "lat": sum(lats) / len(lats),
                    "lon": sum(lons) / len(lons),
                    "name": "Search Area",
                    "source": "feature_centroid"
                }
    except Exception as e:
        print(f"⚠️ Error extracting location: {e}")
    return None

# Flask routes
@app.route('/')
def index():
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle queries with improved smolagents approach."""
    global current_map_state
    print("\n" + "="*50)
    print("🧠 PROCESSING QUERY")
    print("="*50)
    
    data = request.json
    query_text = data.get('query', '')
    print(f"Query: {query_text}")
    current_map_state["last_query"] = query_text
    
    try:
        print("🚀 Running agent...")
        result = agent.run(query_text)
        print(f"🔍 Result type: {type(result)}")
        print(f"🔍 Result preview: {str(result)[:200]}...")
        
        # Process response
        try:
            structured_response = result if isinstance(result, dict) else safe_json_parse(str(result))
            print("✅ Parsed response")
        except Exception as parse_error:
            print(f"❌ Parse error: {parse_error}")
            structured_response = {
                "text_description": "Formatting issue. Try a simpler query.",
                "geojson_data": [],
                "search_location": None,
                "layer_type": "unknown"
            }
        
        # Extract components
        response_text = structured_response.get('text_description', 'Analysis completed')
        geojson_data = structured_response.get('geojson_data', [])
        search_location = structured_response.get('search_location')
        layer_type = structured_response.get('layer_type', 'features')
        print(f"📊 Raw features: {len(geojson_data)}")
        
        # Validate features
        max_features = 500 if layer_type == "cadastral" else 100
        valid_features = validate_and_fix_features(
            geojson_data,
            search_location=search_location,
            radius_km=15
        )
        print(f"✅ Valid features: {len(valid_features)}")
        
        # Update state
        current_map_state["features"] = valid_features
        current_map_state["layer_type"] = layer_type
        current_map_state["search_location"] = search_location
        
        # Create legend
        legend_data = create_flexible_legend_data(valid_features, layer_type)
        
        # Fallback location
        if not search_location and valid_features:
            search_location = extract_search_location_from_response(response_text, valid_features)
            current_map_state["search_location"] = search_location
        
        return jsonify({
            "response": response_text,
            "geojson_data": valid_features[:max_features],
            "search_location": search_location,
            "layer_type": layer_type,
            "legend_data": legend_data,
            "agent_type": "smolagents"
        })
        
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({
            "error": error_msg,
            "response": "Error processing request. Try 'Show buildings in Amsterdam'.",
            "geojson_data": [],
            "search_location": None,
            "layer_type": "unknown",
            "agent_type": "error"
        })
    
    finally:
        print("🎉 PROCESSING COMPLETED")
        print("="*50 + "\n")

@app.route('/api/test-prompt', methods=['GET'])
def test_prompt():
    """Test prompt templates loading."""
    try:
        prompt_templates = load_prompt_templates()
        system_prompt = prompt_templates.get("system_prompt", "")
        return jsonify({
            "prompt_loaded": True,
            "template_sections": list(prompt_templates.keys()),
            "system_prompt_length": len(system_prompt),
            "system_prompt_preview": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "prompt_loaded": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

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
    """Enhanced health check."""
    try:
        prompt_templates = load_prompt_templates()
        system_prompt = prompt_templates.get("system_prompt", "")
        prompt_status = {
            "loaded": True,
            "sections": list(prompt_templates.keys()),
            "system_prompt_length": len(system_prompt),
            "has_content": len(system_prompt) > 100
        }
    except Exception as e:
        prompt_status = {
            "loaded": False,
            "error": str(e)
        }
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_available": tools_available,
        "agent_ready": agent is not None,
        "prompt_status": prompt_status
    })

if __name__ == '__main__':
    print("🚀 Starting IMPROVED Intelligent PDOK Application")
    print("="*40)
    print("🔧 IMPROVEMENTS:")
    print("  ✅ Enhanced feature validation with radius filtering")
    print("  ✅ Modular agent workflow support")
    print("  ✅ Improved legend data for all layers")
    print("  ✅ Robust error handling and logging")
    print("  ✅ Optimized max_features for parcels")
    
    print("\n🧠 FEATURES:")
    print("  ✅ Natural AI intelligence")
    print("  ✅ Detailed debugging")
    print("  ✅ Better response processing")
    
    print("\n🎯 ENHANCED APPROACH:")
    print("  ✅ Strict radius validation")
    print("  ✅ Dynamic legend generation")
    print("  ✅ Improved JSON parsing")
    
    print("\nTEST QUERIES:")
    print("  'Show buildings in Amsterdam'")
    print("  'Agricultural land in Utrecht'")
    print("  'Large parcels in Groningen'")
    
    print(f"\n🌐 http://localhost:5000")
    print("  📊 http://localhost:5000/api/health")
    print("  🧪 http://localhost:5000/api/test-prompt")
    print("="*40)
    
    app.run(debug=True, port=5000, host='0.0.0.0')
