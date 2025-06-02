from tools.pdok_intelligent_agent_tool import EnhancedPDOKIntelligentAgent

def test_building_search():
    agent = EnhancedPDOKIntelligentAgent()
    result = agent.forward("Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²")
    assert not result.get('error'), "Query should succeed"
    assert result['geojson_data'], "Should return buildings"
    assert "area ≥ 300m²" in result['text_description'], "Should apply area filter"
test_building_search()