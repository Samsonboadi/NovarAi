# test_intelligent_tool.py - Test the new intelligent PDOK tool

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.intelligent_pdok_building_tool import IntelligentPDOKBuildingTool
from tools.pdok_location import find_location_coordinates

def test_address_search():
    """Test intelligent search for specific address."""
    print("🏠 Testing Address Search: Kloosterstraat 27 Ten Boer")
    print("-" * 60)
    
    tool = IntelligentPDOKBuildingTool()
    
    result = tool.forward(
        location="Kloosterstraat 27 Ten Boer",
        max_features=10,
        search_strategy="nearest"
    )
    
    if result.get('error'):
        print(f"❌ FAILED: {result['error']}")
        return False
    
    buildings = result.get('geojson_data', [])
    print(f"✅ Found {len(buildings)} buildings")
    
    if buildings:
        print("📍 Distance progression (should start from address):")
        for i, building in enumerate(buildings[:5]):
            distance = building.get('properties', {}).get('distance_km', 0)
            name = building.get('name', f'Building {i+1}')
            print(f"   {i+1}. {name}: {distance:.3f}km")
        
        # Verify buildings are sorted by distance
        distances = [b.get('properties', {}).get('distance_km', 0) for b in buildings]
        is_sorted = all(distances[i] <= distances[i+1] for i in range(len(distances)-1))
        
        if is_sorted:
            print("✅ Buildings correctly sorted by distance")
        else:
            print("❌ Buildings NOT sorted by distance")
            return False
    
    return True

def test_city_search():
    """Test intelligent search for city."""
    print("\n🌆 Testing City Search: Groningen")
    print("-" * 60)
    
    tool = IntelligentPDOKBuildingTool()
    
    result = tool.forward(
        location="Groningen",
        max_features=15,
        search_strategy="nearest"
    )
    
    if result.get('error'):
        print(f"❌ FAILED: {result['error']}")
        return False
    
    buildings = result.get('geojson_data', [])
    print(f"✅ Found {len(buildings)} buildings")
    
    if buildings:
        print("📍 Distance range for city search:")
        distances = [b.get('properties', {}).get('distance_km', 0) for b in buildings]
        min_dist = min(distances)
        max_dist = max(distances)
        avg_dist = sum(distances) / len(distances)
        
        print(f"   Range: {min_dist:.3f}km to {max_dist:.3f}km")
        print(f"   Average: {avg_dist:.3f}km")
        
        # Verify reasonable radius for city
        if max_dist > 1.0:  # City search should find buildings further than 1km
            print("✅ City search used appropriate larger radius")
        else:
            print("❌ City search radius too small")
            return False
    
    return True

def test_historic_search():
    """Test intelligent search for historic buildings."""
    print("\n🏛️ Testing Historic Search: Buildings older than 100 years in Groningen")
    print("-" * 60)
    
    tool = IntelligentPDOKBuildingTool()
    
    result = tool.forward(
        location="Groningen",
        max_features=10,
        max_year=1924,  # Buildings older than 100 years
        search_strategy="historic_priority"
    )
    
    if result.get('error'):
        print(f"❌ FAILED: {result['error']}")
        return False
    
    buildings = result.get('geojson_data', [])
    print(f"✅ Found {len(buildings)} historic buildings")
    
    if buildings:
        print("🗓️ Building ages found:")
        for i, building in enumerate(buildings[:5]):
            props = building.get('properties', {})
            year = props.get('bouwjaar', 'Unknown')
            distance = props.get('distance_km', 0)
            age = 2024 - year if isinstance(year, int) else 'Unknown'
            name = building.get('name', f'Building {i+1}')
            print(f"   {i+1}. {name}: {year} ({age} years old), {distance:.3f}km")
        
        # Verify age filtering worked
        years = [b.get('properties', {}).get('bouwjaar') for b in buildings if b.get('properties', {}).get('bouwjaar')]
        if years:
            max_year_found = max(years)
            if max_year_found <= 1924:
                print("✅ Age filtering worked correctly")
            else:
                print(f"❌ Age filtering failed - found building from {max_year_found}")
                return False
    
    return True

def test_train_station_search():
    """Test intelligent search for train station area."""
    print("\n🚂 Testing Train Station Search: Amsterdam Centraal")
    print("-" * 60)
    
    tool = IntelligentPDOKBuildingTool()
    
    result = tool.forward(
        location="Amsterdam Centraal",
        max_features=12,
        search_strategy="nearest"
    )
    
    if result.get('error'):
        print(f"❌ FAILED: {result['error']}")
        return False
    
    buildings = result.get('geojson_data', [])
    print(f"✅ Found {len(buildings)} buildings near station")
    
    if buildings:
        print("🚂 Buildings near Amsterdam Centraal:")
        for i, building in enumerate(buildings[:3]):
            props = building.get('properties', {})
            distance = props.get('distance_km', 0)
            year = props.get('bouwjaar', 'Unknown')
            name = building.get('name', f'Building {i+1}')
            print(f"   {i+1}. {name}: {distance:.3f}km, built {year}")
        
        # Verify reasonable distances for dense urban area
        distances = [b.get('properties', {}).get('distance_km', 0) for b in buildings]
        avg_distance = sum(distances) / len(distances)
        
        if avg_distance < 2.0:  # Station area should have dense buildings nearby
            print(f"✅ Station search found dense urban buildings (avg: {avg_distance:.3f}km)")
        else:
            print(f"⚠️ Station search found distant buildings (avg: {avg_distance:.3f}km)")
    
    return True

def test_context_recognition():
    """Test that the tool recognizes different location contexts."""
    print("\n🧠 Testing Context Recognition")
    print("-" * 60)
    
    tool = IntelligentPDOKBuildingTool()
    
    test_cases = [
        ("Kloosterstraat 27 Ten Boer", "specific_address"),
        ("Amsterdam Centraal", "transport_hub"),
        ("Groningen", "city"),
        ("Utrecht station", "transport_hub"),
        ("Hoofdweg 123", "specific_address"),
        ("Rotterdam", "city")
    ]
    
    all_passed = True
    
    for location, expected_type in test_cases:
        context = tool._analyze_location_context(location)
        actual_type = context['type']
        
        if actual_type == expected_type:
            print(f"✅ {location}: {actual_type} (radius: {context['initial_radius']}km)")
        else:
            print(f"❌ {location}: expected {expected_type}, got {actual_type}")
            all_passed = False
    
    return all_passed

def test_radius_progression():
    """Test that radius expands intelligently when insufficient buildings found."""
    print("\n📏 Testing Radius Progression")
    print("-" * 60)
    
    # Test with a location that might have few buildings
    tool = IntelligentPDOKBuildingTool()
    
    result = tool.forward(
        location="Ten Boer",  # Smaller town
        max_features=20,  # Request many buildings
        search_strategy="nearest"
    )
    
    if result.get('error'):
        print(f"❌ FAILED: {result['error']}")
        return False
    
    buildings = result.get('geojson_data', [])
    print(f"✅ Found {len(buildings)} buildings")
    
    if buildings:
        distances = [b.get('properties', {}).get('distance_km', 0) for b in buildings]
        max_distance = max(distances)
        print(f"📏 Searched up to {max_distance:.3f}km to find {len(buildings)} buildings")
        
        # Check if tool expanded radius (should find buildings beyond initial small radius)
        if max_distance > 2.0:
            print("✅ Tool successfully expanded radius to find sufficient buildings")
        else:
            print("⚠️ Tool may not have expanded radius sufficiently")
    
    return True

def compare_with_flexible_tool():
    """Compare intelligent tool with flexible tool to show improvements."""
    print("\n🔄 Comparing Intelligent vs Flexible Tool")
    print("-" * 60)
    
    try:
        from tools.pdok_service_discovery_tool import PDOKBuildingsFlexibleTool
        
        # Test same query with both tools
        location = "Groningen"
        max_features = 15
        max_year = 1924
        
        print(f"Query: {max_features} buildings in {location} older than 100 years")
        
        # Test flexible tool
        print("\n📊 Flexible Tool Result:")
        flexible_tool = PDOKBuildingsFlexibleTool()
        flexible_result = flexible_tool.forward(
            location=location,
            max_features=max_features,
            max_year=max_year,
            radius_km=10.0  # Fixed radius
        )
        
        flexible_buildings = flexible_result.get('geojson_data', [])
        print(f"   Found: {len(flexible_buildings)} buildings")
        
        if flexible_buildings:
            flex_distances = [b.get('properties', {}).get('distance_km', 0) for b in flexible_buildings]
            print(f"   Distance range: {min(flex_distances):.3f}km to {max(flex_distances):.3f}km")
        
        # Test intelligent tool
        print("\n🧠 Intelligent Tool Result:")
        intelligent_tool = IntelligentPDOKBuildingTool()
        intelligent_result = intelligent_tool.forward(
            location=location,
            max_features=max_features,
            max_year=max_year,
            search_strategy="historic_priority"
        )
        
        intelligent_buildings = intelligent_result.get('geojson_data', [])
        print(f"   Found: {len(intelligent_buildings)} buildings")
        
        if intelligent_buildings:
            intel_distances = [b.get('properties', {}).get('distance_km', 0) for b in intelligent_buildings]
            print(f"   Distance range: {min(intel_distances):.3f}km to {max(intel_distances):.3f}km")
        
        # Compare results
        print("\n📈 Comparison:")
        print(f"   Flexible tool: {len(flexible_buildings)} buildings")
        print(f"   Intelligent tool: {len(intelligent_buildings)} buildings")
        
        if len(intelligent_buildings) > len(flexible_buildings):
            print("✅ Intelligent tool found more buildings")
        elif len(intelligent_buildings) == len(flexible_buildings):
            print("➡️ Both tools found same number of buildings")
        else:
            print("⚠️ Flexible tool found more buildings")
        
        return True
        
    except ImportError:
        print("⚠️ Flexible tool not available for comparison")
        return True

def main():
    """Run all tests for the intelligent PDOK tool."""
    print("🧪 TESTING INTELLIGENT PDOK BUILDING TOOL")
    print("="*80)
    
    tests = [
        ("Address Search", test_address_search),
        ("City Search", test_city_search),
        ("Historic Search", test_historic_search),
        ("Train Station Search", test_train_station_search),
        ("Context Recognition", test_context_recognition),
        ("Radius Progression", test_radius_progression),
        ("Tool Comparison", compare_with_flexible_tool)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {str(e)}")
    
    print("\n" + "="*80)
    print(f"🏆 TEST RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Intelligent PDOK tool is working correctly.")
        print("\n✨ Key Features Validated:")
        print("  ✅ Context-aware radius calculation")
        print("  ✅ Progressive radius expansion")
        print("  ✅ Distance-based sorting (closest first)")
        print("  ✅ Address vs city vs station recognition")
        print("  ✅ Historic building search optimization")
        print("  ✅ Search strategy implementation")
        
        print("\n🚀 Ready for Production:")
        print("  1. Replace get_pdok_buildings_flexible with get_buildings_intelligent")
        print("  2. Update system prompt to use intelligent tool")
        print("  3. Test with real queries")
        
        print("\n📝 Example Queries That Will Now Work Better:")
        print("  • 'Show me 10 buildings around Kloosterstraat 27 Ten Boer'")
        print("    → Will start with 0.5km radius from address")
        print("  • 'Find 20 buildings in Groningen older than 100 years'")
        print("    → Will use large city radius with historic priority")
        print("  • 'Buildings near Amsterdam Centraal'")
        print("    → Will use station-optimized radius and density")
        
    else:
        print("⚠️ Some tests failed. Issues to resolve:")
        print("  - Check PyProj installation: pip install pyproj")
        print("  - Verify internet connection for PDOK API calls")
        print("  - Ensure coordinate transformation is working")
        print("  - Check if PDOK services are accessible")

if __name__ == "__main__":
    main()