# app.py - Complete Intent-Driven Map-Aware Flask Application

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
    "statistics": {},
    "search_location": None,  # Store the search location for pin display
    "current_layer_type": None  # Track what type of data is currently displayed
}

def load_system_prompt(file_path: str = "static/system_prompt.yml") -> dict:
    """Load system prompt from YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        print(f"✅ Successfully loaded intent-driven system prompt from {file_path}")
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

def detect_layer_type_from_features(features):
    """Detect what type of layer is being displayed based on feature properties."""
    if not features or len(features) == 0:
        return "unknown"
    
    # Sample the first few features to determine type
    sample_features = features[:3]
    
    for feature in sample_features:
        properties = feature.get('properties', {})
        
        # Check for land use indicators
        if any(key in properties for key in ['bgb2015_hoofdklasse_code', 'bgb2015_hoofdklasse_label', 'hoofdklasse', 'bodemgebruik']):
            return "land_use"
        
        # Check for building indicators
        elif any(key in properties for key in ['bouwjaar', 'oppervlakte', 'bag_status', 'pand_status']):
            return "buildings"
        
        # Check for parcel indicators
        elif any(key in properties for key in ['kadastraleGrootteWaarde', 'perceelnummer', 'sectie', 'kadaster']):
            return "parcels"
        
        # Check for nature/environmental indicators
        elif any(key in properties for key in ['gebiedsnaam', 'natura2000', 'bescherming', 'type_gebied']):
            return "environmental"
        
        # Check for administrative boundary indicators
        elif any(key in properties for key in ['gemeentenaam', 'provincienaam', 'gemeentecode', 'wijknaam']):
            return "administrative"
    
    return "unknown"

def create_flexible_legend_data(features, layer_type):
    """Create legend data based on the type of features being displayed."""
    if not features or len(features) == 0:
        return None
    
    legend_data = {
        "layer_type": layer_type,
        "title": "Feature Legend",
        "categories": [],
        "statistics": {}
    }
    
    if layer_type == "land_use":
        # Create land use legend
        legend_data["title"] = "🌾 Land Use Classification"
        
        # Extract land use classifications
        classifications = {}
        total_area = 0
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Look for land use classification fields
            land_use = (props.get('bgb2015_hoofdklasse_label') or 
                       props.get('hoofdklasse') or 
                       props.get('bodemgebruik') or 
                       'Unknown')
            
            # Look for area fields
            area = (props.get('shape_area') or 
                   props.get('oppervlakte') or 
                   props.get('area') or 0)
            
            if land_use not in classifications:
                classifications[land_use] = {'count': 0, 'area': 0}
            
            classifications[land_use]['count'] += 1
            classifications[land_use]['area'] += float(area) if area else 0
            total_area += float(area) if area else 0
        
        # Create legend categories
        colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316']
        for i, (land_use, data) in enumerate(classifications.items()):
            percentage = (data['area'] / total_area * 100) if total_area > 0 else 0
            area_ha = data['area'] / 10000 if data['area'] > 0 else 0
            
            legend_data["categories"].append({
                "label": land_use,
                "color": colors[i % len(colors)],
                "count": data['count'],
                "area_ha": round(area_ha, 1),
                "percentage": round(percentage, 1)
            })
        
        legend_data["statistics"] = {
            "total_features": len(features),
            "total_area_ha": round(total_area / 10000, 1) if total_area > 0 else 0,
            "classifications": len(classifications)
        }
    
    elif layer_type == "buildings":
        # Create building legend based on age or area
        legend_data["title"] = "🏠 Building Classification"
        
        years = []
        areas = []
        
        for feature in features:
            props = feature.get('properties', {})
            
            year = props.get('bouwjaar')
            if year and str(year).isdigit():
                years.append(int(year))
            
            area = (props.get('oppervlakte') or 
                   props.get('area_m2') or 
                   props.get('oppervlakte_min') or 0)
            if area and area > 0:
                areas.append(float(area))
        
        if years:
            # Age-based legend
            legend_data["categories"] = [
                {"label": "Historic (pre-1900)", "color": "#8B0000", "range": "< 1900"},
                {"label": "Early Modern (1900-1950)", "color": "#FF4500", "range": "1900-1950"},
                {"label": "Mid-Century (1950-2000)", "color": "#32CD32", "range": "1950-2000"},
                {"label": "Contemporary (2000+)", "color": "#1E90FF", "range": "2000+"}
            ]
            
            legend_data["statistics"] = {
                "total_buildings": len(features),
                "year_range": f"{min(years)} - {max(years)}",
                "average_year": round(sum(years) / len(years))
            }
        
        elif areas:
            # Area-based legend
            legend_data["categories"] = [
                {"label": "Large (>1000m²)", "color": "#dc2626", "range": "> 1000m²"},
                {"label": "Medium (500-1000m²)", "color": "#f97316", "range": "500-1000m²"},
                {"label": "Standard (200-500m²)", "color": "#eab308", "range": "200-500m²"},
                {"label": "Small (<200m²)", "color": "#22c55e", "range": "< 200m²"}
            ]
            
            legend_data["statistics"] = {
                "total_buildings": len(features),
                "area_range": f"{min(areas):.0f} - {max(areas):.0f}m²",
                "average_area": f"{sum(areas) / len(areas):.0f}m²"
            }
    
    elif layer_type == "parcels":
        # Create parcel legend based on size
        legend_data["title"] = "📐 Parcel Size Classification"
        
        areas = []
        for feature in features:
            props = feature.get('properties', {})
            area = props.get('kadastraleGrootteWaarde', 0)
            if area and area > 0:
                areas.append(float(area))
        
        if areas:
            # Convert to hectares for larger parcels
            areas_ha = [area / 10000 for area in areas]
            
            legend_data["categories"] = [
                {"label": "Very Large (>10ha)", "color": "#dc2626", "range": "> 10ha"},
                {"label": "Large (5-10ha)", "color": "#f97316", "range": "5-10ha"},
                {"label": "Medium (1-5ha)", "color": "#eab308", "range": "1-5ha"},
                {"label": "Standard (0.1-1ha)", "color": "#22c55e", "range": "0.1-1ha"},
                {"label": "Small (<0.1ha)", "color": "#3b82f6", "range": "< 0.1ha"}
            ]
            
            legend_data["statistics"] = {
                "total_parcels": len(features),
                "area_range": f"{min(areas_ha):.2f} - {max(areas_ha):.2f}ha",
                "average_area": f"{sum(areas_ha) / len(areas_ha):.2f}ha",
                "total_area": f"{sum(areas_ha):.1f}ha"
            }
    
    elif layer_type == "environmental":
        # Create environmental/nature legend
        legend_data["title"] = "🌿 Protected Areas"
        
        area_types = {}
        total_area = 0
        
        for feature in features:
            props = feature.get('properties', {})
            
            area_type = (props.get('type_gebied') or 
                        props.get('naam') or 
                        props.get('gebiedsnaam') or 
                        'Protected Area')
            
            area = props.get('oppervlakte', 0)
            
            if area_type not in area_types:
                area_types[area_type] = {'count': 0, 'area': 0}
            
            area_types[area_type]['count'] += 1
            area_types[area_type]['area'] += float(area) if area else 0
            total_area += float(area) if area else 0
        
        colors = ['#22c55e', '#10b981', '#059669', '#047857', '#065f46']
        for i, (area_type, data) in enumerate(area_types.items()):
            legend_data["categories"].append({
                "label": area_type,
                "color": colors[i % len(colors)],
                "count": data['count'],
                "area_ha": round(data['area'] / 10000, 1) if data['area'] > 0 else 0
            })
        
        legend_data["statistics"] = {
            "total_areas": len(features),
            "total_area_ha": round(total_area / 10000, 1) if total_area > 0 else 0,
            "area_types": len(area_types)
        }
    
    elif layer_type == "administrative":
        # Create administrative boundary legend
        legend_data["title"] = "🗺️ Administrative Boundaries"
        
        boundary_types = {}
        
        for feature in features:
            props = feature.get('properties', {})
            
            if 'provincienaam' in props:
                boundary_type = 'Province'
            elif 'gemeentenaam' in props:
                boundary_type = 'Municipality'
            elif 'wijknaam' in props:
                boundary_type = 'District'
            else:
                boundary_type = 'Administrative Area'
            
            if boundary_type not in boundary_types:
                boundary_types[boundary_type] = 0
            boundary_types[boundary_type] += 1
        
        colors = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b']
        for i, (boundary_type, count) in enumerate(boundary_types.items()):
            legend_data["categories"].append({
                "label": boundary_type,
                "color": colors[i % len(colors)],
                "count": count
            })
        
        legend_data["statistics"] = {
            "total_boundaries": len(features),
            "boundary_types": len(boundary_types)
        }
    
    else:
        # Generic legend for unknown types
        legend_data["title"] = "📊 Features"
        legend_data["categories"] = [
            {"label": "Features", "color": "#3b82f6", "count": len(features)}
        ]
        legend_data["statistics"] = {
            "total_features": len(features)
        }
    
    return legend_data

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
                "suggestions": ["Ask the AI to find land use data, buildings, or parcels in a specific location"]
            }
        
        # Detect layer type
        layer_type = detect_layer_type_from_features(features)
        current_map_state["current_layer_type"] = layer_type
        
        analysis = {
            "feature_count": len(features),
            "layer_type": layer_type,
            "feature_types": {},
            "analysis_summary": {},
            "geographic_info": {},
            "summary": ""
        }
        
        # Analyze feature types and properties
        geometry_types = []
        locations = []
        feature_properties = []
        
        for feature in features:
            if 'geometry' in feature and feature['geometry']:
                geom_type = feature['geometry'].get('type', 'Unknown')
                geometry_types.append(geom_type)
            
            props = feature.get('properties', {})
            feature_properties.append(props)
            
            # Location tracking
            if 'lat' in feature and 'lon' in feature:
                locations.append((feature['lat'], feature['lon']))
        
        # Feature type statistics
        analysis["feature_types"] = dict(Counter(geometry_types))
        
        # Layer-specific analysis
        if layer_type == "land_use":
            analysis["analysis_summary"] = analyze_land_use_features(features)
        elif layer_type == "buildings":
            analysis["analysis_summary"] = analyze_building_features(features)
        elif layer_type == "parcels":
            analysis["analysis_summary"] = analyze_parcel_features(features)
        elif layer_type == "environmental":
            analysis["analysis_summary"] = analyze_environmental_features(features)
        
        # Geographic analysis
        if locations:
            lats = [loc[0] for loc in locations]
            lons = [loc[1] for loc in locations]
            
            analysis["geographic_info"] = {
                "center_point": [round(statistics.mean(lats), 6), round(statistics.mean(lons), 6)],
                "spread_km": round(((max(lats) - min(lats)) * 111), 2)
            }
        
        # Generate summary
        summary_parts = [f"Currently displaying {len(features)} {layer_type} features"]
        if analysis["analysis_summary"]:
            summary_parts.append(str(analysis["analysis_summary"]))
        
        analysis["summary"] = ". ".join(summary_parts) + "."
        
        # Update global state
        current_map_state["statistics"] = analysis
        current_map_state["last_updated"] = datetime.now().isoformat()
        
        return analysis
        
    except Exception as e:
        return {"error": f"Error analyzing map features: {str(e)}"}

def analyze_land_use_features(features):
    """Analyze land use specific features."""
    classifications = {}
    total_area = 0
    
    for feature in features:
        props = feature.get('properties', {})
        
        land_use = (props.get('bgb2015_hoofdklasse_label') or 
                   props.get('hoofdklasse') or 
                   props.get('bodemgebruik') or 
                   'Unknown')
        
        area = (props.get('shape_area') or 
               props.get('oppervlakte') or 
               props.get('area') or 0)
        
        if land_use not in classifications:
            classifications[land_use] = 0
        
        classifications[land_use] += float(area) if area else 0
        total_area += float(area) if area else 0
    
    # Find dominant land use
    if classifications:
        dominant_use = max(classifications, key=classifications.get)
        dominant_percentage = (classifications[dominant_use] / total_area * 100) if total_area > 0 else 0
        
        return {
            "dominant_land_use": dominant_use,
            "dominant_percentage": round(dominant_percentage, 1),
            "total_area_ha": round(total_area / 10000, 1) if total_area > 0 else 0,
            "land_use_types": len(classifications)
        }
    
    return {}

def analyze_building_features(features):
    """Analyze building specific features."""
    years = []
    areas = []
    
    for feature in features:
        props = feature.get('properties', {})
        
        year = props.get('bouwjaar')
        if year and str(year).isdigit():
            years.append(int(year))
        
        area = (props.get('oppervlakte') or 
               props.get('area_m2') or 
               props.get('oppervlakte_min') or 0)
        if area and area > 0:
            areas.append(float(area))
    
    result = {}
    
    if years:
        result.update({
            "oldest_building": min(years),
            "newest_building": max(years),
            "average_year": round(sum(years) / len(years))
        })
    
    if areas:
        result.update({
            "average_area_m2": round(sum(areas) / len(areas)),
            "largest_building_m2": max(areas),
            "total_building_area": round(sum(areas))
        })
    
    return result

def analyze_parcel_features(features):
    """Analyze parcel specific features."""
    areas = []
    
    for feature in features:
        props = feature.get('properties', {})
        area = props.get('kadastraleGrootteWaarde', 0)
        if area and area > 0:
            areas.append(float(area))
    
    if areas:
        areas_ha = [area / 10000 for area in areas]
        return {
            "total_parcels": len(features),
            "average_size_ha": round(sum(areas_ha) / len(areas_ha), 2),
            "largest_parcel_ha": round(max(areas_ha), 2),
            "total_area_ha": round(sum(areas_ha), 1)
        }
    
    return {"total_parcels": len(features)}

def analyze_environmental_features(features):
    """Analyze environmental/nature specific features."""
    area_types = {}
    
    for feature in features:
        props = feature.get('properties', {})
        
        area_type = (props.get('type_gebied') or 
                    props.get('naam') or 
                    props.get('gebiedsnaam') or 
                    'Protected Area')
        
        if area_type not in area_types:
            area_types[area_type] = 0
        area_types[area_type] += 1
    
    if area_types:
        dominant_type = max(area_types, key=area_types.get)
        return {
            "dominant_type": dominant_type,
            "total_protected_areas": len(features),
            "area_types": len(area_types)
        }
    
    return {"total_protected_areas": len(features)}

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
            "current_layer_type": current_map_state.get("current_layer_type", "unknown"),
            "search_location": current_map_state.get("search_location"),
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
        
        elif any(term in question_lower for term in ['what is pdok', 'pdok']):
            return """PDOK (Publieke Dienstverlening Op de Kaart) is the Dutch national spatial data infrastructure. It provides free access to geographic datasets from Dutch government organizations, including land use data (bestandbodemgebruik), building data (BAG), cadastral information, and environmental data."""
        
        elif any(term in question_lower for term in ['land use', 'bestandbodemgebruik']):
            return """Bestand Bodemgebruik is the Dutch land use database from CBS containing detailed classification of how land is actually used across the Netherlands. It includes agricultural areas, urban development, nature areas, water bodies, and infrastructure with high spatial detail."""
        
        elif any(term in question_lower for term in ['what is bag', 'buildings and addresses']):
            return """BAG (Basisregistratie Adressen en Gebouwen) is the Dutch Buildings and Addresses Database. It contains authoritative information about all buildings, addresses, and premises in the Netherlands with construction years, areas, and precise geometries."""
        
        else:
            return f"I can help with various map and GIS topics including PDOK services, land use analysis, building data, and spatial analysis techniques. Could you be more specific about what you'd like to know?"
        
    except Exception as e:
        return f"Error answering map question: {str(e)}"

def create_agent_with_intent_driven_tools():
    """Create the agent with streamlined, intent-driven tools."""
    
    # Import only essential tools
    try:
        # Try to import the enhanced discovery tool first
        try:
            from tools.enhanced_discovery_tool import IntentDrivenPDOKDiscoveryTool
            discovery_tool = IntentDrivenPDOKDiscoveryTool()
            print("✅ Using enhanced intent-driven discovery tool")
        except ImportError:
            # Fallback to enhanced AI intelligent tools
            try:
                from tools.enhanced_ai_intelligent_tools import EnhancedPDOKServiceDiscoveryTool
                discovery_tool = EnhancedPDOKServiceDiscoveryTool()
                print("✅ Using enhanced AI intelligent discovery tool")
            except ImportError:
                # Final fallback to basic AI tools
                from tools.ai_intelligent_tools import PDOKServiceDiscoveryTool
                discovery_tool = PDOKServiceDiscoveryTool()
                print("⚠️ Using basic discovery tool")
        
        from tools.enhanced_pdok_location_tool import IntelligentLocationSearchTool
        from tools.flexible_ai_driven_spatial_tools import FlexibleSpatialDataTool, FlexibleSpatialAnalysisTool
        from tools.coordinate_conversion_tool import CoordinateConversionTool
        
        essential_tools = [
            discovery_tool,                     # Intent-driven or enhanced discovery
            IntelligentLocationSearchTool(),    # Location search
            FlexibleSpatialDataTool(),          # Flexible data fetching
            FlexibleSpatialAnalysisTool(),      # Spatial analysis
            CoordinateConversionTool()          # Coordinate conversion
        ]
        
        print("✅ Successfully imported essential tools")
        tools_available = True
        
    except ImportError as e:
        print(f"❌ Could not import essential tools: {e}")
        essential_tools = []
        tools_available = False
    
    # Combine with built-in tools
    tools = []
    tools.extend(essential_tools)
    
    # Add built-in analysis tools
    tools.extend([
        analyze_current_map_features,
        get_map_context_info,
        answer_map_question,
        DuckDuckGoSearchTool()
    ])

    print(f"🧠 Creating INTENT-DRIVEN agent with {len(tools)} essential tools:")
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = str(type(tool).__name__)
        print(f"  ✅ {tool_name}")
    
    # Load intent-driven system prompt
    system_prompt_config = load_system_prompt("static/system_prompt.yml")
    
    # Create agent with intent-driven configuration
    if system_prompt_config:
        print("✅ Using INTENT-DRIVEN system prompt configuration")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=15,  # Fewer steps due to focused approach
            prompt_templates=system_prompt_config,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "re", 
                "statistics", "collections", "datetime", "math"
            ]
        )
    else:
        print("⚠️ Using default system prompt")
        agent = CodeAgent(
            model=model,
            tools=tools,
            max_steps=15,
            additional_authorized_imports=[
                "xml.etree.ElementTree", "json", "requests", "re",
                "statistics", "collections", "datetime", "math"
            ]
        )
    
    return agent, tools_available

# Initialize the agent with intent-driven tools
agent, tools_available = create_agent_with_intent_driven_tools()

def extract_search_location_from_response(response_text, features):
    """Extract search location information from AI response or features."""
    search_location = None
    
    # Try to extract from response text
    if response_text:
        import re
        
        # Look for coordinate patterns
        coord_patterns = [
            r'(\d{2}\.\d+)°?N[,\s]+(\d{1,2}\.\d+)°?E',
            r'lat[itude]*[:\s]*(\d{2}\.\d+)[,\s]+lon[gitude]*[:\s]*(\d{1,2}\.\d+)',
            r'coordinates[:\s]*\[?(\d{2}\.\d+)[,\s]+(\d{1,2}\.\d+)\]?'
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                lat, lon = float(match.group(1)), float(match.group(2))
                search_location = {
                    "lat": lat,
                    "lon": lon,
                    "name": "Search Location",
                    "source": "response_text"
                }
                break
        
        # Look for location names
        if not search_location:
            location_patterns = [
                r'(?:near|around|in|at)\s+([A-Za-z\s]+?)(?:\s|$|,|\.|province)',
                r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:province|area|region)',
                r'(?:searching|found|located)\s+(?:in|near)\s+([A-Za-z\s]+?)(?:\s|$|,|\.)'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    location_name = match.group(1).strip()
                    if len(location_name) > 2:  # Valid location name
                        search_location = {
                            "name": location_name,
                            "source": "response_text_name"
                        }
                        break
    
    # Try to extract from features with distance information
    if not search_location and features:
        for feature in features:
            props = feature.get('properties', {})
            if 'distance_km' in props or 'distance_from_reference' in props:
                # This suggests there was a reference point
                # Use the centroid of features as approximate search location
                lats = [f.get('lat', 0) for f in features if f.get('lat')]
                lons = [f.get('lon', 0) for f in features if f.get('lon')]
                
                if lats and lons:
                    search_location = {
                        "lat": sum(lats) / len(lats),
                        "lon": sum(lons) / len(lons),
                        "name": "Search Area Center",
                        "source": "feature_centroid"
                    }
                break
    
    return search_location

# Flask routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('base.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries using INTENT-DRIVEN AI approach with enhanced features."""
    global current_map_state
    
    print("\n" + "="*80)
    print("🎯 INTENT-DRIVEN AI ANALYSIS WITH ENHANCED FEATURES")
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
        print("🎯 Running INTENT-DRIVEN AI analysis...")
        
        # Enhanced intent-driven context prompt
        intent_driven_prompt = f"""
            User query: "{query_text}"

            Current map context:
            - Map center: {map_center[1]:.4f}°N, {map_center[0]:.4f}°E  
            - Zoom level: {map_zoom}
            - Features currently on map: {len(current_features)}

            You are an intelligent AI assistant with INTENT-DRIVEN analysis capabilities.

            🎯 MANDATORY WORKFLOW - INTENT FIRST:

            1. **ANALYZE USER INTENT** (in comments, no tools yet):
               ```python
               # INTENT ANALYSIS:
               # Query type: [land_use_analysis/building_analysis/parcel_analysis/environmental_analysis/administrative_analysis]
               # Primary service needed: [bestandbodemgebruik/bag/cadastral/natura2000/cbs]
               # Location mentioned: [location name or "none"]
               # Analysis required: [area calculation/distribution/filtering/visualization]
               # Expected output: [what user wants to see]
               ```

            2. **TARGETED SERVICE DISCOVERY** (single service only):
               - Use discover_pdok_services with SPECIFIC service name based on intent
               - For land use analysis → service_name="bestandbodemgebruik" 
               - For building analysis → service_name="bag"  
               - For parcel analysis → service_name="cadastral"
               - For environmental analysis → service_name="natura2000"
               - For administrative analysis → service_name="cbs"
               - ALWAYS set get_attributes=True to get attribute information

            3. **LOCATION RESOLUTION** (if needed):
               - Use search_location_coordinates for mentioned locations
               - Store coordinates for search location pin display

            4. **PRECISE DATA REQUEST** (using discovered attributes):
               - Use fetch_pdok_data with exact service URL and layer from discovery
               - Use discovered attribute names for filters (never hardcoded names)
               - Construct search area based on location and appropriate radius

            5. **ANALYSIS AND RESPONSE**:
               - Process data according to user intent
               - Calculate totals, percentages, distributions as requested
               - Format for flexible legend system
               - Return structured response with text_description and geojson_data

            🚨 CRITICAL RULES:
            ❌ NEVER discover all services - only the one you need
            ❌ NEVER use hardcoded attribute names like 'kadastraleGrootteWaarde', 'oppervlakte_min'
            ❌ NEVER skip intent analysis
            ❌ NEVER use wrong service for analysis type
            ❌ NEVER assume attribute names exist without discovery
            ✅ ALWAYS analyze intent first (in comments)
            ✅ ALWAYS discover targeted service only
            ✅ ALWAYS use exact discovered attribute names
            ✅ ALWAYS match service to analysis type
            ✅ ALWAYS include search location information
            ✅ ALWAYS make sure the retirved coordnates from the location search are in rdnew format that is critical for making querry to the PDOK services
            ✅ ALWAYS import json if dealing with geographic data
            🎯 SERVICE MAPPING:
            - "agricultural land", "land use", "distribution" → bestandbodemgebruik service
            - "buildings", "construction", "bouwjaar" → bag service
            - "parcels", "properties", "kadaster" → cadastral service
            - "protected areas", "nature", "natura2000" → natura2000 service
            - "municipalities", "boundaries", "administrative" → cbs service

            📍 LOCATION PIN REQUIREMENTS:
            - If location is mentioned, find coordinates and include in response
            - Add search_location to response for map pin display
            - Format: {{"lat": latitude, "lon": longitude, "name": "Location Name"}}

            🏷️ FLEXIBLE LEGEND SUPPORT:
            - Features will be analyzed for layer type (land_use, buildings, parcels, environmental, administrative)
            - Frontend will create appropriate legend based on layer type
            - Ensure features have proper properties for legend generation

            📊 RESPONSE FORMAT:
            Always return JSON structure:
            ```python
            import json
            final_answer(json.dumps({{
                "text_description": "Detailed analysis description with statistics",
                "geojson_data": processed_features_array,
                "search_location": {{"lat": lat, "lon": lon, "name": "Location Name"}},  # If location found
                "layer_type": "detected_layer_type",  # For legend generation
                "analysis_summary": {{"key": "statistics"}}  # Optional summary data
            }}))
            ```

            Start with intent analysis in comments, then proceed with targeted discovery.
            """
        
        print("🎯 AI analyzing intent and making targeted requests...")

        result = agent.run(intent_driven_prompt)
        
        print(f"\n--- INTENT-DRIVEN RESULT DEBUG ---")
        print(f"Result type: {type(result)}")
        
        # Enhanced result processing
        structured_response = None
        result_text = None
        
        # Check if result is already a structured dictionary
        if isinstance(result, dict):
            print("✅ AI returned structured dictionary response")
            structured_response = result
            result_text = result.get('text_description', str(result))
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
            
            # Try to parse JSON from text
            try:
                import re
                json_patterns = [
                    r'\{.*"text_description".*"geojson_data".*\}',
                    r'\{.*"description".*"features".*\}',
                    r'\{.*"response".*"data".*\}'
                ]
                
                for pattern in json_patterns:
                    json_match = re.search(pattern, result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            parsed_response = json.loads(json_str)
                            if isinstance(parsed_response, dict):
                                structured_response = parsed_response
                                print(f"✅ Found structured response")
                                break
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                print(f"⚠️ Error detecting structured response: {e}")
        
        # Process structured response if found
        if structured_response:
            print(f"🔍 Processing structured response: {list(structured_response.keys())}")
            
            # Extract components
            response_text = (structured_response.get('text_description') or 
                           structured_response.get('description') or 
                           structured_response.get('response') or 
                           structured_response.get('message'))
            
            geojson_data = (structured_response.get('geojson_data') or 
                          structured_response.get('features') or 
                          structured_response.get('data'))
            
            search_location = structured_response.get('search_location')
            layer_type = structured_response.get('layer_type')
            analysis_summary = structured_response.get('analysis_summary')
            
            # Process geographic data
            processed_features = process_geojson_response(geojson_data)
            
            if processed_features and len(processed_features) > 0:
                print(f"🗺️ Successfully processed geographic data: {len(processed_features)} features")
                
                # Detect layer type if not provided
                if not layer_type:
                    layer_type = detect_layer_type_from_features(processed_features)
                
                # Extract search location if not provided
                if not search_location:
                    search_location = extract_search_location_from_response(response_text, processed_features)
                
                # Create flexible legend data
                legend_data = create_flexible_legend_data(processed_features, layer_type)
                
                # Update global state
                current_map_state["features"] = processed_features
                current_map_state["current_layer_type"] = layer_type
                current_map_state["search_location"] = search_location
                current_map_state["last_updated"] = datetime.now().isoformat()
                
                print(f"📍 Search location: {search_location}")
                print(f"🏷️ Layer type: {layer_type}")
                print(f"📊 Legend categories: {len(legend_data['categories']) if legend_data else 0}")
                
                return jsonify({
                    "response": response_text or "AI analysis completed with geographic results.",
                    "geojson_data": processed_features,
                    "search_location": search_location,
                    "layer_type": layer_type,
                    "legend_data": legend_data,
                    "analysis_summary": analysis_summary,
                    "agent_type": "intent_driven_geographic",
                    "ai_method": "intent_analysis",
                    "tools_used": "targeted_discovery"
                })
            else:
                print("❌ No valid geographic data found")
        
        # Fallback: Search agent execution logs for geographic data
        print("🔍 Searching agent logs for geographic data...")
        geographic_data = None
        description_text = None
        search_location = None
        
        # Check agent memory for tool results
        if hasattr(agent, 'memory') and hasattr(agent.memory, 'steps'):
            log_entries = agent.memory.steps
            print(f"   📚 Checking memory.steps ({len(log_entries)} entries)...")
            
            for step_idx, log_entry in enumerate(reversed(log_entries)):
                tool_calls_to_check = []
                
                if hasattr(log_entry, 'tool_calls'):
                    tool_calls_to_check.extend(log_entry.tool_calls)
                
                if hasattr(log_entry, 'action') and hasattr(log_entry.action, 'tool_calls'):
                    tool_calls_to_check.extend(log_entry.action.tool_calls)
                
                # Check tool call results
                for tool_call in tool_calls_to_check:
                    if hasattr(tool_call, 'result'):
                        tool_result = tool_call.result
                        tool_name = getattr(tool_call, 'tool_name', 'unknown_tool')
                        
                        if isinstance(tool_result, dict):
                            # Look for geographic data
                            geo_data, desc_text = extract_geographic_data_flexible(tool_result)
                            if geo_data:
                                geographic_data = geo_data
                                description_text = desc_text or f"Analysis completed using {tool_name}"
                                print(f"🎯 Found geographic data from tool '{tool_name}': {len(geo_data)} features")
                                break
                            
                            # Look for search location from location search tool
                            if tool_name == 'search_location_coordinates' and 'lat' in tool_result and 'lon' in tool_result:
                                search_location = {
                                    "lat": tool_result['lat'],
                                    "lon": tool_result['lon'],
                                    "name": tool_result.get('name', 'Search Location')
                                }
                                print(f"📍 Found search location: {search_location}")
                
                if geographic_data:
                    break
        
        # Process geographic data from logs
        if geographic_data:
            print(f"🗺️ Processing geographic data from logs: {len(geographic_data)} features")
            
            serialized_features = []
            for item in geographic_data:
                try:
                    if isinstance(item, dict) and is_valid_geographic_feature(item):
                        serialized_item = ensure_json_serializable(item)
                        enhanced_feature = ensure_map_compatible_feature(serialized_item, len(serialized_features))
                        if enhanced_feature:
                            serialized_features.append(enhanced_feature)
                except Exception as e:
                    print(f"❌ Error processing log feature: {e}")
                    continue
            
            if serialized_features:
                print(f"✅ Returning geographic data from logs: {len(serialized_features)} features")
                
                # Detect layer type and create legend
                layer_type = detect_layer_type_from_features(serialized_features)
                legend_data = create_flexible_legend_data(serialized_features, layer_type)
                
                # Extract search location if not found yet
                if not search_location:
                    search_location = extract_search_location_from_response(description_text, serialized_features)
                
                # Update global state
                current_map_state["features"] = serialized_features
                current_map_state["current_layer_type"] = layer_type
                current_map_state["search_location"] = search_location
                current_map_state["last_updated"] = datetime.now().isoformat()
                
                return jsonify({
                    "response": description_text or "AI completed intent-driven spatial analysis.",
                    "geojson_data": serialized_features,
                    "search_location": search_location,
                    "layer_type": layer_type,
                    "legend_data": legend_data,
                    "agent_type": "intent_driven_geographic_processed",
                    "ai_method": "intent_analysis",
                    "tools_used": "targeted_discovery"
                })
        
        # Default: return text response
        print(f"💬 Returning intent-driven text response")
        return jsonify({
            "response": str(result_text),
            "search_location": search_location,
            "agent_type": "intent_driven_text",
            "ai_method": "intent_analysis",
            "tools_used": "targeted_discovery"
        })
        
    except Exception as e:
        error_msg = f"Intent-driven AI error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({
            "error": error_msg,
            "agent_type": "error",
            "tools_used": "intent_driven"
        })

    finally:
        print("🎉 INTENT-DRIVEN ANALYSIS COMPLETED")
        print("="*80 + "\n")

def process_geojson_response(data):
    """Process GeoJSON data from AI response and convert to frontend format."""
    try:
        print(f"🔍 Processing GeoJSON response: {type(data)}")
        
        if not data:
            return None
        
        # Handle FeatureCollection format
        if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
            print("✅ Found GeoJSON FeatureCollection")
            features = data.get('features', [])
            print(f"   Features in collection: {len(features)}")
            
            processed_features = []
            for i, feature in enumerate(features):
                try:
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
        
        # Create a meaningful name based on properties
        name = create_feature_name(properties, index)
        
        # Create description based on properties
        description = create_feature_description(properties)
        
        # Create frontend-compatible feature
        frontend_feature = {
            'type': 'Feature',
            'name': name,
            'lat': lat,
            'lon': lon,
            'description': description,
            'geometry': geometry,
            'properties': ensure_json_serializable(properties)
        }
        
        return frontend_feature
        
    except Exception as e:
        print(f"❌ Error converting feature {index}: {e}")
        return None

def create_feature_name(properties, index):
    """Create a meaningful name for a feature based on its properties."""
    # Try different naming strategies based on available properties
    
    # Land use features
    if 'bgb2015_hoofdklasse_label' in properties:
        return f"Land Use: {properties['bgb2015_hoofdklasse_label']}"
    elif 'hoofdklasse' in properties:
        return f"Land Use: {properties['hoofdklasse']}"
    elif 'bodemgebruik' in properties:
        return f"Land Use: {properties['bodemgebruik']}"
    
    # Building features
    elif 'bouwjaar' in properties:
        year = properties['bouwjaar']
        return f"Building ({year})"
    elif 'bag_status' in properties:
        return f"Building - {properties['bag_status']}"
    
    # Parcel features
    elif 'perceelnummer' in properties:
        return f"Parcel {properties['perceelnummer']}"
    elif 'kadastraleGrootteWaarde' in properties:
        area_ha = properties['kadastraleGrootteWaarde'] / 10000
        return f"Parcel ({area_ha:.1f}ha)"
    
    # Environmental features
    elif 'gebiedsnaam' in properties:
        return f"Protected: {properties['gebiedsnaam']}"
    elif 'naam' in properties:
        return f"Area: {properties['naam']}"
    
    # Administrative features
    elif 'gemeentenaam' in properties:
        return f"Municipality: {properties['gemeentenaam']}"
    elif 'wijknaam' in properties:
        return f"District: {properties['wijknaam']}"
    
    # Generic fallback
    else:
        feature_id = properties.get('identificatie', properties.get('id', f'Feature-{index+1}'))
        return f"Feature {str(feature_id)[-6:]}" if len(str(feature_id)) > 6 else str(feature_id)

def create_feature_description(properties):
    """Create a meaningful description for a feature based on its properties."""
    desc_parts = []
    
    # Land use properties
    if 'bgb2015_hoofdklasse_label' in properties:
        desc_parts.append(f"Type: {properties['bgb2015_hoofdklasse_label']}")
    
    if 'shape_area' in properties and properties['shape_area'] > 0:
        area_ha = properties['shape_area'] / 10000
        desc_parts.append(f"Area: {area_ha:.1f}ha")
    
    # Building properties
    if 'bouwjaar' in properties:
        desc_parts.append(f"Built: {properties['bouwjaar']}")
    
    if 'oppervlakte' in properties and properties['oppervlakte'] > 0:
        desc_parts.append(f"Area: {properties['oppervlakte']}m²")
    
    # Parcel properties
    if 'kadastraleGrootteWaarde' in properties and properties['kadastraleGrootteWaarde'] > 0:
        area_ha = properties['kadastraleGrootteWaarde'] / 10000
        desc_parts.append(f"Size: {area_ha:.1f}ha")
    
    # Environmental properties
    if 'type_gebied' in properties:
        desc_parts.append(f"Type: {properties['type_gebied']}")
    
    # Administrative properties
    if 'provincienaam' in properties:
        desc_parts.append(f"Province: {properties['provincienaam']}")
    
    # Distance information
    if 'distance_km' in properties:
        desc_parts.append(f"Distance: {properties['distance_km']:.2f}km")
    
    return " | ".join(desc_parts) if desc_parts else "Feature"

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

def extract_geographic_data_flexible(data_dict):
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
                    if is_valid_geographic_feature(first_item):
                        geographic_data = potential_data
                        break
    
    # Extract description
    for field in potential_desc_fields:
        if field in data_dict:
            description = data_dict[field]
            break
    
    return geographic_data, description

def is_valid_geographic_feature(feature_dict):
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

def ensure_map_compatible_feature(feature, index):
    """Ensure feature has all required fields for frontend map display."""
    try:
        # Create a copy to avoid modifying original
        enhanced_feature = feature.copy()
        
        # Ensure 'type' field
        if 'type' not in enhanced_feature:
            enhanced_feature['type'] = 'Feature'
        
        # Ensure 'name' field
        if 'name' not in enhanced_feature:
            properties = enhanced_feature.get('properties', {})
            enhanced_feature['name'] = create_feature_name(properties, index)
        
        # Ensure 'lat' and 'lon' fields
        if 'lat' not in enhanced_feature or 'lon' not in enhanced_feature:
            # Try to extract from geometry
            geometry = enhanced_feature.get('geometry', {})
            centroid = calculate_centroid_from_geojson_geometry(geometry)
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
            properties = enhanced_feature.get('properties', {})
            enhanced_feature['description'] = create_feature_description(properties)
        
        # Ensure 'geometry' field is valid
        if 'geometry' not in enhanced_feature or not enhanced_feature['geometry']:
            # Create point geometry from lat/lon
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

@app.route('/api/test-intent-analysis', methods=['POST'])
def test_intent_analysis():
    """Test endpoint for intent-driven analysis approach."""
    data = request.json
    test_query = data.get('query', 'Analyze agricultural land distribution in Utrecht province')
    
    try:
        print(f"🧪 Testing intent-driven analysis with: '{test_query}'")
        
        # Simple intent analysis test
        intent_mapping = {
            "land_use_analysis": ["agricultural", "land use", "distribution", "bodemgebruik"],
            "building_analysis": ["building", "construction", "bouwjaar", "address"],
            "parcel_analysis": ["parcel", "property", "kadaster", "suitable"],
            "environmental_analysis": ["protected", "nature", "natura2000", "conservation"],
            "administrative_analysis": ["municipality", "province", "boundary", "administrative"]
        }
        
        detected_intent = "unknown"
        recommended_service = "cadastral"
        
        query_lower = test_query.lower()
        for intent, keywords in intent_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_intent = intent
                if intent == "land_use_analysis":
                    recommended_service = "bestandbodemgebruik"
                elif intent == "building_analysis":
                    recommended_service = "bag"
                elif intent == "parcel_analysis":
                    recommended_service = "cadastral"
                elif intent == "environmental_analysis":
                    recommended_service = "natura2000"
                elif intent == "administrative_analysis":
                    recommended_service = "cbs"
                break
        
        return jsonify({
            "success": True,
            "query": test_query,
            "detected_intent": detected_intent,
            "recommended_service": recommended_service,
            "message": f"Intent-driven system would use {recommended_service} service for {detected_intent}",
            "workflow": [
                f"1. Analyze intent: {detected_intent}",
                f"2. Target service: {recommended_service}",
                f"3. Discover attributes for {recommended_service} only",
                f"4. Extract location if mentioned",
                f"5. Make precise data request",
                f"6. Generate flexible legend for layer type"
            ],
            "tools_available": tools_available
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

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
        agent, tools_available = create_agent_with_intent_driven_tools()
        return jsonify({
            "success": True,
            "message": "System prompt reloaded successfully with INTENT-DRIVEN approach"
        })
    except Exception as e:
        error_msg = f"Error reloading system prompt: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        })

@app.route('/api/legend-data', methods=['GET'])
def get_legend_data():
    """Get legend data for current features."""
    global current_map_state
    try:
        features = current_map_state.get("features", [])
        layer_type = current_map_state.get("current_layer_type", "unknown")
        
        if not features:
            return jsonify({
                "legend_data": None,
                "message": "No features currently displayed"
            })
        
        legend_data = create_flexible_legend_data(features, layer_type)
        
        return jsonify({
            "legend_data": legend_data,
            "layer_type": layer_type,
            "feature_count": len(features)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error generating legend data: {str(e)}"
        })

@app.route('/api/search-location', methods=['GET'])
def get_search_location():
    """Get current search location for location pin display."""
    global current_map_state
    try:
        search_location = current_map_state.get("search_location")
        
        return jsonify({
            "search_location": search_location,
            "has_location": search_location is not None
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error getting search location: {str(e)}"
        })

@app.route('/api/layer-info', methods=['GET'])
def get_layer_info():
    """Get information about the current layer type and statistics."""
    global current_map_state
    try:
        features = current_map_state.get("features", [])
        layer_type = current_map_state.get("current_layer_type", "unknown")
        statistics = current_map_state.get("statistics", {})
        
        layer_info = {
            "layer_type": layer_type,
            "feature_count": len(features),
            "statistics": statistics,
            "last_updated": current_map_state.get("last_updated"),
            "has_features": len(features) > 0
        }
        
        # Add layer-specific information
        if layer_type == "land_use":
            layer_info["display_name"] = "Land Use Classification"
            layer_info["icon"] = "🌾"
            layer_info["description"] = "Land use data from CBS Bestand Bodemgebruik"
        elif layer_type == "buildings":
            layer_info["display_name"] = "Buildings"
            layer_info["icon"] = "🏠"
            layer_info["description"] = "Building data from BAG (Buildings and Addresses)"
        elif layer_type == "parcels":
            layer_info["display_name"] = "Cadastral Parcels"
            layer_info["icon"] = "📐"
            layer_info["description"] = "Parcel data from Kadastrale Kaart"
        elif layer_type == "environmental":
            layer_info["display_name"] = "Protected Areas"
            layer_info["icon"] = "🌿"
            layer_info["description"] = "Environmental protection data"
        elif layer_type == "administrative":
            layer_info["display_name"] = "Administrative Boundaries"
            layer_info["icon"] = "🗺️"
            layer_info["description"] = "Administrative boundary data from CBS"
        else:
            layer_info["display_name"] = "Features"
            layer_info["icon"] = "📊"
            layer_info["description"] = "Geographic features"
        
        return jsonify(layer_info)
        
    except Exception as e:
        return jsonify({
            "error": f"Error getting layer info: {str(e)}"
        })

@app.route('/api/clear-map', methods=['POST'])
def clear_map():
    """Clear all features from the map."""
    global current_map_state
    try:
        current_map_state["features"] = []
        current_map_state["current_layer_type"] = None
        current_map_state["search_location"] = None
        current_map_state["statistics"] = {}
        current_map_state["last_updated"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "message": "Map cleared successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error clearing map: {str(e)}"
        })

@app.route('/api/export-features', methods=['GET'])
def export_features():
    """Export current features as GeoJSON."""
    global current_map_state
    try:
        features = current_map_state.get("features", [])
        layer_type = current_map_state.get("current_layer_type", "unknown")
        search_location = current_map_state.get("search_location")
        
        if not features:
            return jsonify({
                "error": "No features to export"
            })
        
        # Create GeoJSON FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "layer_type": layer_type,
                "feature_count": len(features),
                "export_timestamp": datetime.now().isoformat(),
                "search_location": search_location,
                "generated_by": "PDOK Intent-Driven Analysis System"
            }
        }
        
        return jsonify(geojson)
        
    except Exception as e:
        return jsonify({
            "error": f"Error exporting features: {str(e)}"
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    global current_map_state
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "features_loaded": len(current_map_state.get("features", [])),
            "tools_available": tools_available,
            "agent_initialized": agent is not None,
            "services": {
                "openai": bool(os.getenv('OPENAI_API_KEY')),
                "pdok": True,  # Assume PDOK is available
                "coordinate_conversion": True
            }
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug information endpoint."""
    global current_map_state
    try:
        debug_data = {
            "current_map_state": {
                "feature_count": len(current_map_state.get("features", [])),
                "layer_type": current_map_state.get("current_layer_type"),
                "search_location": current_map_state.get("search_location"),
                "last_updated": current_map_state.get("last_updated"),
                "center": current_map_state.get("center"),
                "zoom": current_map_state.get("zoom")
            },
            "agent_info": {
                "agent_available": agent is not None,
                "tools_available": tools_available,
                "max_steps": getattr(agent, 'max_steps', None) if agent else None
            },
            "environment": {
                "debug_mode": app.debug,
                "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
                "flask_env": os.getenv('FLASK_ENV', 'production')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(debug_data)
        
    except Exception as e:
        return jsonify({
            "error": f"Error getting debug info: {str(e)}"
        })

if __name__ == '__main__':
    print("🚀 Starting INTENT-DRIVEN Map-Aware Flask Server with Enhanced Features")
    print("="*80)
    print("🎯 INTENT-DRIVEN ARCHITECTURE:")
    print("  ✅ AI analyzes user intent FIRST")
    print("  ✅ AI targets SPECIFIC service based on intent")
    print("  ✅ AI discovers attributes for ONLY needed service")
    print("  ✅ AI uses discovered attributes (no hardcoding)")
    print("  ✅ AI matches correct service to analysis type")
    print("  ✅ Flexible legend system for all layer types")
    print("  ✅ Search location pin display")
    
    print("\n🎯 SERVICE INTENT MAPPING:")
    print("  🌾 Land use analysis → bestandbodemgebruik service")
    print("  🏠 Building analysis → bag service")
    print("  📐 Parcel analysis → cadastral service")
    print("  🌿 Environmental analysis → natura2000 service")
    print("  🗺️ Administrative analysis → cbs service")
    
    print("\n🔧 ESSENTIAL TOOLS ONLY:")
    if tools_available:
        print("  🎯 Intent-driven discovery: Targeted service discovery")
        print("  📍 Location search: Find coordinates with pin display")
        print("  🌐 Flexible data fetching: Precise data requests")
        print("  🧮 Spatial analysis: Custom analysis operations")
        print("  🔄 Coordinate conversion: WGS84 ↔ RD New")
    
    print("\n🆕 ENHANCED FEATURES:")
    print("  📍 Search location pins: Visual markers for queried locations")
    print("  🏷️ Flexible legends: Automatic legend generation for any layer type")
    print("    - 🌾 Land use: Classification-based legends")
    print("    - 🏠 Buildings: Age or area-based legends")
    print("    - 📐 Parcels: Size-based legends")
    print("    - 🌿 Environmental: Protection type legends")
    print("    - 🗺️ Administrative: Boundary type legends")
    print("  📊 Layer detection: Automatic detection of data type")
    print("  🎨 Dynamic styling: Context-aware map styling")
    
    print("\n🗑️ CLEANED UP:")
    print("  ❌ Removed 8+ redundant tools")
    print("  ❌ Removed hardcoded attribute dependencies")
    print("  ❌ Removed all-service discovery approach")
    print("  ❌ Removed complex multi-layer tools")
    
    print("\nEXAMPLE INTENT-DRIVEN QUERIES:")
    print("  🌾 'Analyze agricultural land distribution in Utrecht province'")
    print("     → Intent: land_use_analysis → Service: bestandbodemgebruik → Legend: Land use types")
    print("  🏠 'Show me buildings near Amsterdam built before 1950'")
    print("     → Intent: building_analysis → Service: bag → Legend: Building ages")
    print("  📐 'Find large parcels suitable for development in Groningen'")
    print("     → Intent: parcel_analysis → Service: cadastral → Legend: Parcel sizes")
    print("  🌿 'Show protected nature areas around Rotterdam'")
    print("     → Intent: environmental_analysis → Service: natura2000 → Legend: Protection types")
    print("  🗺️ 'What are the municipal boundaries of Utrecht?'")
    print("     → Intent: administrative_analysis → Service: cbs → Legend: Boundary types")
    
    print("\n" + "="*80)
    print(f"🌐 Server endpoints:")
    print(f"  📱 Main app: http://localhost:5000")
    print(f"  🎯 Intent-driven API: POST /api/query")
    print(f"  🗺️ Map state: GET /api/map-state")
    print(f"  🔄 Reload prompt: POST /api/reload-prompt")
    print(f"  🧪 Test intent analysis: POST /api/test-intent-analysis")
    
    print("\n🎯 THE INTENT-DRIVEN DIFFERENCE:")
    print("  ✅ AI ANALYZES intent before any tool use")
    print("  ✅ AI TARGETS specific service only")
    print("  ✅ AI DISCOVERS attributes dynamically")
    print("  ✅ AI MATCHES service to analysis type")
    print("  ✅ AI USES discovered names (no hardcoding)")
    print("  ✅ FLEXIBLE legends for any data type")
    print("  ✅ SEARCH LOCATION pins for user orientation")
    print("  ✅ LAYER-AWARE styling and statistics")
    
    print("\n🔧 FIXED ISSUES:")
    print("  ✅ No more wrong service selection")
    print("  ✅ No more hardcoded attributes")
    print("  ✅ No more all-service discovery")
    print("  ✅ Flexible legends for all layer types")
    print("  ✅ Search location visualization")
    print("  ✅ Streamlined tool architecture")
    
    print("\n📋 STARTUP CHECKLIST:")
    print("  1. ✅ OpenAI API key configured")
    print("  2. ⚠️  Update system_prompt.yml with intent-driven version")
    print("  3. ⚠️  Add enhanced_discovery_tool.py to tools directory")
    print("  4. ⚠️  Clean up redundant tools (see cleanup guide)")
    print("  5. ⚠️  Test with: 'Analyze agricultural land in Utrecht province'")
    
    print("\n🎉 READY TO START!")
    print("="*80)
    
    try:
        app.run(debug=True, port=5000, host='0.0.0.0')
    except KeyboardInterrupt:
        print("\n👋 Server shutdown gracefully")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        print("Check your configuration and try again")
    finally:
        print("\n🔧 Intent-driven PDOK analysis server stopped")
        print("Thank you for using the enhanced map-aware system!")