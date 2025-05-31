# test_flexible_tools.py - Test the new flexible PDOK tools

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.pdok_service_discovery_tool import (
    PDOKServiceDiscoveryTool,
    PDOKDataRequestTool,
    PDOKDataFilterTool,
    PDOKMapDisplayTool,
    PDOKBuildingsFlexibleTool
)
from tools.pdok_location import find_location_coordinates

def test_service_discovery():
    """Test the service discovery tool."""
    print("🔍 Testing PDOK Service Discovery...")
    
    discovery_tool = PDOKServiceDiscoveryTool()
    
    # Test discovering all services
    result = discovery_tool.forward("all")
    print(f"✅ All services: {len(result.get('services', {}))} found")
    
    # Test specific service
    bag_result = discovery_tool.forward("bag")
    print(f"✅ BAG service: {bag_result.get('service', {}).get('name', 'Not found')}")
    
    return result

def test_data_request():
    """Test the data request tool."""
    print("\n🌐 Testing PDOK Data Request...")
    
    # Get Groningen coordinates
    location_result = find_location_coordinates("Groningen")
    if location_result.get('error'):
        print(f"❌ Could not find Groningen: {location_result['error']}")
        return None
    
    lat, lon = location_result['lat'], location_result['lon']
    print(f"📍 Groningen coordinates: {lat:.6f}, {lon:.6f}")
    
    request_tool = PDOKDataRequestTool()
    
    # Request building data
    result = request_tool.forward(
        service_url="https://service.pdok.nl/lv/bag/wfs/v2_0",
        layer_name="bag:pand",
        center_lat=lat,
        center_lon=lon,
        radius_km=3.0,
        max_features=50
    )
    
    if result.get('error'):
        print(f"❌ Data request failed: {result['error']}")
        return None
    
    print(f"✅ Received {result.get('count', 0)} buildings from PDOK")
    return result

def test_data_filtering(raw_data):
    """Test the data filtering tool."""
    if not raw_data or raw_data.get('error'):
        print("\n❌ Skipping filter test - no data to filter")
        return None
    
    print("\n🔽 Testing PDOK Data Filtering...")
    
    # Get Groningen coordinates
    location_result = find_location_coordinates("Groningen")
    lat, lon = location_result['lat'], location_result['lon']
    
    filter_tool = PDOKDataFilterTool()
    
    # Test filtering for old buildings within 2km
    filtered_result = filter_tool.forward(
        features=raw_data,
        center_lat=lat,
        center_lon=lon,
        max_distance_km=2.0,
        max_year=1970,  # Buildings older than ~50 years
        sort_by="distance",
        limit=10
    )
    
    if filtered_result.get('error'):
        print(f"❌ Filtering failed: {filtered_result['error']}")
        return None
    
    print(f"✅ Filtered to {filtered_result.get('count', 0)} old buildings within 2km")
    
    # Show sample results
    features = filtered_result.get('filtered_features', [])
    for i, feature in enumerate(features[:3]):
        props = feature.get('properties', {})
        distance = feature.get('distance_km', 'Unknown')
        year = feature.get('building_year', 'Unknown')
        print(f"   {i+1}. Distance: {distance:.3f}km, Year: {year}")
    
    return filtered_result

def test_map_display(filtered_data):
    """Test the map display formatting tool."""
    if not filtered_data or filtered_data.get('error'):
        print("\n❌ Skipping display test - no filtered data")
        return None
    
    print("\n🗺️ Testing Map Display Formatting...")
    
    display_tool = PDOKMapDisplayTool()
    
    result = display_tool.forward(
        filtered_data=filtered_data,
        location_name="Groningen",
        search_description="buildings older than 50 years within 2km"
    )
    
    if result.get('error'):
        print(f"❌ Display formatting failed: {result['error']}")
        return None
    
    geojson_data = result.get('geojson_data', [])
    text_desc = result.get('text_description', '')
    
    print(f"✅ Formatted {len(geojson_data)} features for map display")
    print(f"📝 Text description length: {len(text_desc)} characters")
    print(f"🔤 First 200 chars: {text_desc[:200]}...")
    
    return result

def test_flexible_building_tool():
    """Test the combined flexible building tool."""
    print("\n🏗️ Testing Flexible Building Tool (Combined)...")
    
    flexible_tool = PDOKBuildingsFlexibleTool()
    
    # Test with buildings older than 100 years in Groningen
    result = flexible_tool.forward(
        location="Groningen",
        max_features=15,
        max_year=1924,  # Buildings older than 100 years
        radius_km=10.0,  # Larger radius for historic buildings
    )
    
    if result.get('error'):
        print(f"❌ Flexible tool failed: {result['error']}")
        return None
    
    geojson_data = result.get('geojson_data', [])
    text_desc = result.get('text_description', '')
    
    print(f"✅ Found {len(geojson_data)} historic buildings")
    print(f"📝 Description: {text_desc[:150]}...")
    
    # Show sample buildings
    for i, building in enumerate(geojson_data[:3]):
        props = building.get('properties', {})
        year = props.get('bouwjaar', 'Unknown')
        distance = props.get('distance_km', 'Unknown')
        name = building.get('name', f'Building {i+1}')
        print(f"   {i+1}. {name} - Built {year}, {distance:.3f}km away")
    
    return result

def main():
    """Run all tests."""
    print("🧪 TESTING FLEXIBLE PDOK TOOLS")
    print("="*50)
    
    try:
        # Test 1: Service Discovery
        services = test_service_discovery()
        
        # Test 2: Data Request
        raw_data = test_data_request()
        
        # Test 3: Data Filtering
        filtered_data = test_data_filtering(raw_data)
        
        # Test 4: Map Display
        display_result = test_map_display(filtered_data)
        
        # Test 5: Combined Flexible Tool
        flexible_result = test_flexible_building_tool()
        
        print("\n" + "="*50)
        print("🎉 ALL TESTS COMPLETED")
        
        # Summary
        tests_passed = 0
        tests_total = 5
        
        if services and not services.get('error'):
            tests_passed += 1
            print("✅ Service Discovery: PASSED")
        else:
            print("❌ Service Discovery: FAILED")
        
        if raw_data and not raw_data.get('error'):
            tests_passed += 1
            print("✅ Data Request: PASSED")
        else:
            print("❌ Data Request: FAILED")
        
        if filtered_data and not filtered_data.get('error'):
            tests_passed += 1
            print("✅ Data Filtering: PASSED")
        else:
            print("❌ Data Filtering: FAILED")
        
        if display_result and not display_result.get('error'):
            tests_passed += 1
            print("✅ Map Display: PASSED")
        else:
            print("❌ Map Display: FAILED")
        
        if flexible_result and not flexible_result.get('error'):
            tests_passed += 1
            print("✅ Flexible Building Tool: PASSED")
        else:
            print("❌ Flexible Building Tool: FAILED")
        
        print(f"\n🏆 SCORE: {tests_passed}/{tests_total} tests passed")
        
        if tests_passed == tests_total:
            print("🎊 ALL TESTS PASSED! Flexible PDOK tools are working correctly.")
            print("\nYou can now:")
            print("  1. Update your app.py to use the new flexible tools")
            print("  2. Test building queries like 'show buildings in Groningen older than 100 years'")
            print("  3. The agent can now discover PDOK services automatically")
            print("  4. Distance filtering should work correctly now")
        else:
            print("⚠️ Some tests failed. Check the error messages above.")
            print("Make sure you have:")
            print("  - PyProj installed: pip install pyproj")
            print("  - Internet connection for PDOK API calls")
            print("  - All tool files in the correct location")
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        print("Check that all dependencies are installed and files are in place.")

if __name__ == "__main__":
    main()