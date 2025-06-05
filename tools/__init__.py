# tools/__init__.py - CLEANED UP - Essential Tools Only

"""
PDOK Tools Registry - Streamlined for Intent-Driven Analysis

This module contains only the essential tools needed for the AI agent to perform
intelligent, intent-driven geospatial analysis with PDOK services.

CORE PHILOSOPHY:
- Intent-driven discovery (not all-service discovery)
- Attribute-based filtering (not hardcoded attributes)  
- Service-specific targeting (not generic approaches)
- Minimal tool set (not tool proliferation)
"""

# Essential Discovery Tool
from tools.enhanced_discovery_tool import IntentDrivenPDOKDiscoveryTool

# Essential Location Services
from tools.enhanced_pdok_location_tool import (
    IntelligentLocationSearchTool, 
    SpecializedAddressSearchTool
)

# Essential Data Fetching
from tools.flexible_ai_driven_spatial_tools import (
    FlexibleSpatialDataTool,
    FlexibleSpatialAnalysisTool    
)

# Essential Coordinate Conversion
from tools.coordinate_conversion_tool import (
    CoordinateConversionTool, 
    CreateRDBoundingBoxTool
)

# Export only essential tools
__all__ = [
    # Intent-driven discovery
    "IntentDrivenPDOKDiscoveryTool",
    
    # Location services
    "IntelligentLocationSearchTool",
    "SpecializedAddressSearchTool", 
    
    # Flexible data fetching
    "FlexibleSpatialDataTool",
    "FlexibleSpatialAnalysisTool",
    
    # Coordinate conversion
    "CoordinateConversionTool",
    "CreateRDBoundingBoxTool"
]

def print_available_tools():
    """Print information about available ESSENTIAL tools."""
    print("🔧 ESSENTIAL PDOK TOOLS (Cleaned Up):")
    print("="*50)
    
    print("🎯 INTENT-DRIVEN DISCOVERY:")
    print("  • IntentDrivenPDOKDiscoveryTool - Targeted service discovery based on user intent")
    print("    - Supports: bestandbodemgebruik, bag, cadastral, natura2000, cbs, bgt, wetlands")
    print("    - Returns: Specific attributes for targeted analysis")
    
    print("\n📍 LOCATION SERVICES:")
    print("  • IntelligentLocationSearchTool - Enhanced location search with type detection")
    print("  • SpecializedAddressSearchTool - Precise address lookup")
    
    print("\n🌐 FLEXIBLE DATA FETCHING:")
    print("  • FlexibleSpatialDataTool - AI-driven data retrieval from any PDOK service")
    print("  • FlexibleSpatialAnalysisTool - Custom spatial analysis operations")
    
    print("\n🔄 COORDINATE CONVERSION:")
    print("  • CoordinateConversionTool - WGS84 to RD New conversion")
    print("  • CreateRDBoundingBoxTool - Create bounding boxes in RD New")
    
    print("\n✨ KEY IMPROVEMENTS:")
    print("  ✅ Intent-driven approach - AI analyzes user intent first")
    print("  ✅ Targeted discovery - Only discover the service you need")
    print("  ✅ Attribute-driven - Use discovered attributes, not hardcoded names")
    print("  ✅ Service-specific - Match correct service to analysis type")
    print("  ✅ Streamlined - Removed redundant and deprecated tools")
    
    print("\n🗑️ REMOVED TOOLS (Deprecated):")
    removed_tools = [
        "ai_intelligent_tools.py",
        "enhanced_ai_intelligent_tools.py", 
        "enhanced_multi_layer_spatial_tool.py",
        "kadaster_tool.py",
        "pdok_building_tool.py",
        "pdok_intelligent_agent_tool.py",
        "pdok_modular_tools.py",
        "pdok_service_discovery_tool.py"
    ]
    
    for tool in removed_tools:
        print(f"  ❌ {tool} - Replaced by intent-driven approach")

def validate_essential_tools():
    """Validate that essential tools are working correctly."""
    print("\n🧪 VALIDATING ESSENTIAL TOOLS...")
    
    try:
        # Test intent-driven discovery
        discovery_tool = IntentDrivenPDOKDiscoveryTool()
        
        # Test targeted discovery (not all services)
        result = discovery_tool.forward("bestandbodemgebruik", get_attributes=True)
        
        if result.get('error'):
            print("❌ Intent-driven discovery failed")
            return False
        else:
            print("✅ Intent-driven discovery working")
        
        # Test location search
        location_tool = IntelligentLocationSearchTool()
        location_result = location_tool.forward("Utrecht")
        
        if location_result.get('error'):
            print("❌ Location search failed")
            return False
        else:
            print("✅ Location search working")
        
        # Test flexible data tool
        spatial_tool = FlexibleSpatialDataTool()
        print("✅ Flexible spatial tools available")
        
        print("🎉 All essential tools validated successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

# Intent-to-Service mapping for AI guidance
INTENT_SERVICE_MAPPING = {
    "land_use_analysis": {
        "service": "bestandbodemgebruik",
        "url": "https://service.pdok.nl/cbs/bestandbodemgebruik/2015/wfs/v1_0",
        "layer": "bestandbodemgebruik:bestand_bodemgebruik_2015",
        "keywords": ["agricultural", "land use", "planning", "distribution"]
    },
    "building_analysis": {
        "service": "bag", 
        "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
        "layer": "bag:pand",
        "keywords": ["building", "construction", "address", "bouwjaar"]
    },
    "parcel_analysis": {
        "service": "cadastral",
        "url": "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0", 
        "layer": "kadastralekaart:Perceel",
        "keywords": ["parcel", "property", "boundary", "kadaster"]
    },
    "environmental_analysis": {
        "service": "natura2000",
        "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
        "layer": "natura2000:natura2000", 
        "keywords": ["protected", "nature", "conservation", "environment"]
    },
    "administrative_analysis": {
        "service": "cbs",
        "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
        "layer": "varies",
        "keywords": ["municipality", "province", "boundary", "administrative"]
    }
}

def get_service_for_intent(user_query: str) -> dict:
    """
    Helper function to map user query to appropriate service.
    This can be used by the AI for intent analysis.
    """
    query_lower = user_query.lower()
    
    for intent, service_info in INTENT_SERVICE_MAPPING.items():
        if any(keyword in query_lower for keyword in service_info["keywords"]):
            return {
                "intent": intent,
                "recommended_service": service_info["service"],
                "service_url": service_info["url"],
                "primary_layer": service_info["layer"],
                "confidence": "high" if len([k for k in service_info["keywords"] if k in query_lower]) > 1 else "medium"
            }
    
    return {
        "intent": "unknown",
        "recommended_service": "cadastral",  # Safe default
        "confidence": "low",
        "note": "Could not determine intent - using default cadastral service"
    }

# Auto-run information when module is imported
if __name__ == "__main__":
    print_available_tools()
    validate_essential_tools()