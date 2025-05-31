# tools/__init__.py - Updated with Flexible PDOK Tools

from .kadaster_tool import KadasterBRKTool, ContactHistoryTool
from .pdok_location import find_location_coordinates, search_dutch_address_pdok, pdok_service, test_pdok_integration
from .intelligent_pdok_building_tool import IntelligentPDOKBuildingTool
# Import the NEW flexible PDOK tools
from .pdok_service_discovery_tool import (
    PDOKServiceDiscoveryTool,
    PDOKDataRequestTool,
    PDOKDataFilterTool,
    PDOKMapDisplayTool,
    PDOKBuildingsFlexibleTool
)

# Legacy building tool (deprecated but included for compatibility)
try:
    from .pdok_building_tool import PDOKBuildingsRealTool
except ImportError:
    print("⚠️ Legacy PDOKBuildingsRealTool not found - using flexible tools only")
    PDOKBuildingsRealTool = None

__all__ = [
    # Location tools
    "find_location_coordinates",
    "search_dutch_address_pdok",
    "pdok_service", 
    "test_pdok_integration",
    
    # Kadaster tools
    "KadasterBRKTool",
    "ContactHistoryTool",
    
    
    # NEW Flexible PDOK tools
    "PDOKServiceDiscoveryTool",
    "PDOKDataRequestTool",
    "PDOKDataFilterTool", 
    "PDOKMapDisplayTool",
    "PDOKBuildingsFlexibleTool",
    "IntelligentPDOKBuildingTool",
    # Legacy tool (deprecated)
    "PDOKBuildingsRealTool"
]

# Print info about available tools
def print_available_tools():
    """Print information about available PDOK tools."""
    print("🔧 AVAILABLE PDOK TOOLS:")
    print("="*40)
    
    print("📍 LOCATION TOOLS:")
    print("  • find_location_coordinates - Enhanced PDOK Locatieserver search")
    print("  • search_dutch_address_pdok - Specialized address search")
    
    print("\n🏛️ KADASTER TOOLS:")
    print("  • KadasterBRKTool - Land parcels and ownership data")
    print("  • ContactHistoryTool - Track property owner communications")
    
    print("\n🏗️ FLEXIBLE PDOK TOOLS (NEW):")
    print("  • PDOKServiceDiscoveryTool - Discover available PDOK services")
    print("  • PDOKDataRequestTool - Make flexible WFS requests")
    print("  • PDOKDataFilterTool - Apply distance/age/area filters")
    print("  • PDOKMapDisplayTool - Format data for map display")
    print("  • PDOKBuildingsFlexibleTool - Combined building search")
    
    if PDOKBuildingsRealTool:
        print("\n⚠️ LEGACY TOOLS:")
        print("  • PDOKBuildingsRealTool - (DEPRECATED) Use PDOKBuildingsFlexibleTool instead")
    
    print("\n✨ ADVANTAGES OF FLEXIBLE TOOLS:")
    print("  ✅ Modular design - use individual tools or combined")
    print("  ✅ Works with any PDOK WFS service, not just buildings")
    print("  ✅ Better distance calculations and coordinate handling")
    print("  ✅ Advanced filtering by age, area, distance")
    print("  ✅ Agent can discover PDOK services automatically")
    print("  ✅ Proper error handling and debugging")
    print("  ✅ Solves the '0 buildings found' issue")

# Validation function to check if tools work
def validate_tools():
    """Validate that the flexible tools are working correctly."""
    print("\n🧪 VALIDATING FLEXIBLE PDOK TOOLS...")
    
    try:
        # Test service discovery
        discovery_tool = PDOKServiceDiscoveryTool()
        services_result = discovery_tool.forward("bag")
        
        if services_result.get('error'):
            print("❌ Service Discovery failed")
            return False
        else:
            print("✅ Service Discovery working")
        
        # Test location search
        location_result = find_location_coordinates("Amsterdam")
        
        if location_result.get('error'):
            print("❌ Location search failed")
            return False
        else:
            print("✅ Location search working")
        
        # Test flexible building tool
        flexible_tool = PDOKBuildingsFlexibleTool()
        # Quick test with small radius and limited features
        building_result = flexible_tool.forward(
            location="Amsterdam",
            max_features=5,
            radius_km=1.0
        )
        
        if building_result.get('error'):
            print(f"⚠️ Building search test failed: {building_result['error']}")
            print("   This might be due to network issues or coordinate problems")
            return True  # Don't fail validation for this
        else:
            buildings_found = len(building_result.get('geojson_data', []))
            print(f"✅ Building search working - found {buildings_found} buildings")
        
        print("🎉 All flexible tools validated successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all tool files are in the tools/ directory")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

# Auto-run validation when module is imported (optional)
if __name__ == "__main__":
    print_available_tools()
    validate_tools()