# tools/enhanced_pdok_location_tool.py - Intelligent Location Search Tool for AI Agent

import requests
import json
import re
from typing import Dict, List, Optional, Union
from smolagents import Tool

class IntelligentLocationSearchTool(Tool):
    """
    Intelligent Dutch location search tool that automatically detects query types
    and provides comprehensive location data with coordinates and administrative details.
    """
    
    name = "find_location_coordinates"
    description = """Intelligent Dutch location search using PDOK Locatieserver API with automatic type detection.

This tool automatically determines the best search approach for any Dutch location query.
It intelligently selects search types, optimizes queries, and provides comprehensive location data.

**When to use this tool:**
- When you need to find coordinates for any Dutch location
- To search for addresses, cities, streets, or landmarks in the Netherlands  
- When converting location names to geographic coordinates
- For validating and enriching location information
- When you need administrative details (municipality, province, postal code)

**What this tool can find:**
- Specific addresses (street + house number)
- Cities and municipalities
- Neighborhoods and districts  
- Street names and roads
- Postal codes (Dutch format: 1234AB)
- Train stations and public landmarks
- Public spaces and landmarks

**Input examples:**
- "Amsterdam Centraal station"
- "Damrak 1, Amsterdam"
- "1012AB" (postal code)
- "Utrecht"
- "Kloosterstraat Ten Boer"
- "Rotterdam city center"

**Output includes:**
- Precise latitude/longitude coordinates
- Detailed description with administrative info
- Location type and precision level
- Confidence score for the match
- Complete administrative metadata

**Special features:**
- Automatic query optimization for better results
- Intelligent search type selection based on query content
- Advanced scoring algorithm for best result selection
- Handles various Dutch location formats and naming conventions"""

    inputs = {
        "query": {
            "type": "string", 
            "description": "Any Dutch location query in natural language (address, city, postal code, landmark, etc.)"
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"
        self.free_endpoint = f"{self.base_url}/free"
        self.user_agent = "PDOK-WebMap-Chat/1.0"
        
        # Search type configurations for intelligent selection
        self.search_types = {
            'adres': {
                'name': 'Address search',
                'keywords': ['address', 'street', 'house number', 'huisnummer', 'straat'],
                'priority': 10
            },
            'gemeente': {
                'name': 'Municipality search',
                'keywords': ['city', 'municipality', 'gemeente', 'town'],
                'priority': 8
            },
            'woonplaats': {
                'name': 'Residential place search',
                'keywords': ['neighborhood', 'area', 'district', 'woonplaats'],
                'priority': 7
            },
            'weg': {
                'name': 'Street/road search',
                'keywords': ['street', 'road', 'avenue', 'lane', 'weg', 'straat', 'laan'],
                'priority': 6
            },
            'postcode': {
                'name': 'Postal code search',
                'keywords': ['postcode', 'postal code', 'zip'],
                'priority': 9
            }
        }
    
    def forward(self, query: str) -> Dict:
        """
        Execute intelligent location search for Dutch locations.
        
        Args:
            query: Location query in natural language
            
        Returns:
            Dictionary with location data including coordinates and administrative details
        """
        try:
            print(f"🧠 Intelligent location search: '{query}'")
            
            # Intelligent search type selection
            search_types = self._determine_search_types(query)
            print(f"🎯 Selected search types: {search_types}")
            
            # Execute optimized search
            result = self._execute_search(query, search_types)
            
            if result.get('error'):
                # Try fallback search with broader types
                print("🔄 Trying fallback search...")
                fallback_types = "adres,woonplaats,gemeente,weg"
                result = self._execute_search(query, fallback_types)
            
            return result
            
        except Exception as e:
            error_msg = f"Location search error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def _determine_search_types(self, query: str) -> str:
        """Intelligently determine the best search types for a query."""
        query_lower = query.lower()
        
        # Score each search type
        type_scores = {}
        
        for search_type, config in self.search_types.items():
            score = config['priority']  # Base priority score
            
            # Keyword matching
            for keyword in config['keywords']:
                if keyword in query_lower:
                    score += 20
            
            # Pattern-based scoring
            if search_type == 'adres':
                # Look for address patterns (numbers, common address words)
                if re.search(r'\d+', query) or any(word in query_lower for word in ['nummer', 'huisnummer', 'address']):
                    score += 15
                    
            elif search_type == 'postcode':
                # Dutch postcode pattern (4 digits + 2 letters)
                if re.search(r'\d{4}\s*[a-zA-Z]{2}', query):
                    score += 30
                    
            elif search_type == 'gemeente':
                # Common Dutch city indicators
                if any(word in query_lower for word in [
                    'amsterdam', 'rotterdam', 'utrecht', 'groningen', 'eindhoven',
                    'tilburg', 'almere', 'breda', 'nijmegen', 'enschede', 'haarlem',
                    'arnhem', 'zaanstad', 'haarlemmermeer', 'zoetermeer', 'emmen'
                ]):
                    score += 25
                    
            elif search_type == 'weg':
                # Street/road indicators
                if any(word in query_lower for word in [
                    'straat', 'laan', 'weg', 'plein', 'kade', 'gracht',
                    'avenue', 'street', 'road', 'boulevard'
                ]):
                    score += 20
            
            type_scores[search_type] = score
        
        # Select top scoring types
        sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 3-4 types with scores above threshold
        selected_types = []
        for search_type, score in sorted_types:
            if score >= 5 and len(selected_types) < 4:
                selected_types.append(search_type)
        
        # Ensure at least basic types are included
        if not selected_types:
            selected_types = ['adres', 'woonplaats', 'gemeente']
        
        return ','.join(selected_types)
    
    def _execute_search(self, query: str, search_types: str) -> Dict:
        """Execute the PDOK search with optimized parameters."""
        try:
            # Optimize query for better results
            optimized_query = self._optimize_query(query)
            
            params = {
                'q': optimized_query,
                'rows': 15,
                'start': 0,
                'fl': 'id identificatie weergavenaam bron type centroide_ll centroide_rd gemeentenaam provincienaam woonplaatsnaam straatnaam huisnummer postcode score',
                'fq': f'type:({search_types.replace(",", " OR ")})',
                'df': 'tekst',
                'wt': 'json',
                'sort': 'score desc'
            }
            
            print(f"🌐 PDOK API request: {optimized_query} | types: {search_types}")
            
            response = requests.get(
                self.free_endpoint,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if not docs:
                return {"error": f"No results found for '{query}' with types {search_types}"}
            
            print(f"📦 PDOK returned {len(docs)} results")
            
            # Select best result
            best_result = self._select_best_result(docs, query)
            
            if not best_result:
                return {"error": f"No suitable location found for '{query}'"}
            
            # Extract comprehensive location data
            location_data = self._extract_location_data(best_result, query)
            
            print(f"✅ Selected: {location_data.get('name', 'Unknown')}")
            print(f"📍 Coordinates: {location_data.get('lat', 0):.6f}, {location_data.get('lon', 0):.6f}")
            
            return location_data
            
        except requests.exceptions.RequestException as e:
            return {"error": f"PDOK API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Search execution error: {str(e)}"}
    
    def _optimize_query(self, query: str) -> str:
        """Optimize the search query for better PDOK results."""
        # Remove common stop words that don't help with location search
        stop_words = ['the', 'de', 'het', 'een', 'a', 'an', 'near', 'close to', 'around']
        
        words = query.split()
        optimized_words = [word for word in words if word.lower() not in stop_words]
        optimized = ' '.join(optimized_words).strip()
        
        # Handle common location patterns
        optimized = optimized.replace('train station', 'station')
        optimized = optimized.replace('city center', 'centrum')
        optimized = optimized.replace('central station', 'centraal')
        
        return optimized or query
    
    def _select_best_result(self, docs: List[Dict], original_query: str) -> Optional[Dict]:
        """Select the best result using intelligent scoring."""
        if not docs:
            return None
        
        query_lower = original_query.lower()
        scored_results = []
        
        for doc in docs:
            score = 0
            
            # Extract key fields
            doc_type = doc.get('type', '').lower()
            weergavenaam = doc.get('weergavenaam', '').lower()
            straatnaam = doc.get('straatnaam', '').lower()
            woonplaatsnaam = doc.get('woonplaatsnaam', '').lower()
            gemeentenaam = doc.get('gemeentenaam', '').lower()
            
            # Type-based scoring
            type_scores = {
                'adres': 35,      # Most specific
                'postcode': 30,   # Very specific
                'woonplaats': 25, # Good specificity
                'gemeente': 20,   # Moderate specificity
                'weg': 15         # Less specific
            }
            score += type_scores.get(doc_type, 5)
            
            # Text matching
            query_words = query_lower.split()
            for word in query_words:
                if len(word) >= 2:
                    if word in weergavenaam: score += 25
                    if word in straatnaam: score += 20
                    if word in woonplaatsnaam: score += 15
                    if word in gemeentenaam: score += 12
            
            # Quality indicators
            if doc.get('centroide_ll'): score += 15
            if doc.get('huisnummer'): score += 10
            if doc.get('postcode'): score += 8
            
            # PDOK's relevance score
            api_score = doc.get('score', 0)
            if api_score: score += float(api_score) * 2
            
            scored_results.append((score, doc))
        
        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        print(f"🏆 Top results:")
        for i, (score, result) in enumerate(scored_results[:3]):
            print(f"  {i+1}. Score: {score:.1f} - {result.get('weergavenaam', 'Unknown')}")
        
        return scored_results[0][1] if scored_results else None
    
    def _extract_location_data(self, doc: Dict, original_query: str) -> Dict:
        """Extract comprehensive location data from PDOK result."""
        try:
            # Extract coordinates
            centroide = doc.get('centroide_ll')
            lat, lon = 0.0, 0.0
            
            if centroide:
                if isinstance(centroide, str):
                    # Handle POINT(lon lat) format
                    coords = centroide.replace('POINT(', '').replace(')', '').split()
                    if len(coords) == 2:
                        lon, lat = float(coords[0]), float(coords[1])
                elif isinstance(centroide, list) and len(centroide) == 2:
                    lon, lat = float(centroide[0]), float(centroide[1])
            
            # Build comprehensive description
            weergavenaam = doc.get('weergavenaam', original_query)
            description_parts = []
            
            # Address components
            if doc.get('straatnaam') and doc.get('huisnummer'):
                description_parts.append(f"Address: {doc.get('straatnaam')} {doc.get('huisnummer')}")
            elif doc.get('straatnaam'):
                description_parts.append(f"Street: {doc.get('straatnaam')}")
            
            # Administrative components
            if doc.get('postcode'):
                description_parts.append(f"Postcode: {doc.get('postcode')}")
            if doc.get('woonplaatsnaam'):
                description_parts.append(f"Place: {doc.get('woonplaatsnaam')}")
            if doc.get('gemeentenaam'):
                description_parts.append(f"Municipality: {doc.get('gemeentenaam')}")
            if doc.get('provincienaam'):
                description_parts.append(f"Province: {doc.get('provincienaam')}")
            
            description = " | ".join(description_parts) if description_parts else weergavenaam
            
            # Determine precision and confidence
            precision = self._determine_precision(doc)
            confidence = self._calculate_confidence(doc)
            
            return {
                "name": weergavenaam,
                "lat": lat,
                "lon": lon,
                "description": description,
                "place_type": doc.get('type', 'unknown'),
                "precision": precision,
                "confidence": confidence,
                "pdok_data": {
                    "id": doc.get('id'),
                    "identificatie": doc.get('identificatie'),
                    "type": doc.get('type'),
                    "gemeente": doc.get('gemeentenaam'),
                    "provincie": doc.get('provincienaam'),
                    "postcode": doc.get('postcode'),
                    "straatnaam": doc.get('straatnaam'),
                    "huisnummer": doc.get('huisnummer'),
                    "woonplaats": doc.get('woonplaatsnaam'),
                    "bron": doc.get('bron'),
                    "score": doc.get('score')
                }
            }
            
        except Exception as e:
            print(f"❌ Error extracting location data: {e}")
            return {
                "name": original_query,
                "lat": 0.0,
                "lon": 0.0,
                "description": f"PDOK result: {doc.get('weergavenaam', original_query)}",
                "error": f"Could not extract coordinates: {str(e)}"
            }
    
    def _determine_precision(self, doc: Dict) -> str:
        """Determine the precision level of the location."""
        if doc.get('huisnummer'):
            return "address_level"  # Most precise
        elif doc.get('straatnaam'):
            return "street_level"
        elif doc.get('woonplaatsnaam'):
            return "neighborhood_level"
        elif doc.get('gemeentenaam'):
            return "municipality_level"
        else:
            return "region_level"
    
    def _calculate_confidence(self, doc: Dict) -> float:
        """Calculate confidence score for the location match."""
        confidence = 0.5  # Base confidence
        
        # Boost based on data completeness
        if doc.get('centroide_ll'): confidence += 0.2
        if doc.get('huisnummer'): confidence += 0.1
        if doc.get('postcode'): confidence += 0.1
        
        # Boost based on PDOK's score
        api_score = doc.get('score', 0)
        if api_score and api_score > 5:
            confidence += min(0.2, api_score / 50)
        
        return min(1.0, confidence)
    
    def is_in_netherlands(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Netherlands boundaries."""
        return (50.7 <= lat <= 53.6) and (3.2 <= lon <= 7.3)


class SpecializedAddressSearchTool(Tool):
    """
    Specialized tool for precise Dutch address searches with enhanced accuracy.
    """
    
    name = "search_dutch_address"
    description = """Specialized tool for finding specific Dutch addresses with enhanced precision.

This tool is optimized specifically for address searches and provides the most
accurate results for street addresses with house numbers.

**When to use this tool:**
- When you need to find a specific street address
- When you have a complete or partial address with street name
- For address validation and standardization  
- When you need precise coordinates for a building or property

**Best for queries like:**
- "Kloosterstraat 27, Ten Boer"
- "Damrak 1 Amsterdam"
- "Prinsengracht 263"
- "Museumplein 6, Amsterdam"

**Output provides:**
- Exact address coordinates
- Standardized address format
- Postal code and administrative details
- Building-level precision indicators"""

    inputs = {
        "address_query": {
            "type": "string", 
            "description": "Specific address query with street name and preferably house number"
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.location_tool = IntelligentLocationSearchTool()
    
    def forward(self, address_query: str) -> Dict:
        """
        Search for specific Dutch addresses with enhanced precision.
        
        Args:
            address_query: Specific address query
            
        Returns:
            Dictionary with detailed address information and precise coordinates
        """
        try:
            print(f"🏠 Specialized address search: '{address_query}'")
            
            # Use the location tool with address-specific optimization
            result = self.location_tool.forward(address_query)
            
            if not result.get('error'):
                # Enhance result with address-specific metadata
                if result.get('place_type') == 'adres':
                    result['address_verified'] = True
                    result['precision_level'] = 'building'
                else:
                    result['address_verified'] = False
                    result['precision_level'] = result.get('precision', 'unknown')
                
                print(f"✅ Found address: {result.get('name')}")
                return result
            else:
                return {"error": f"No address found for '{address_query}': {result.get('error')}"}
                
        except Exception as e:
            error_msg = f"Address search error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}


# Export functions for backward compatibility
def find_location_coordinates(query: str) -> dict:
    """Wrapper function for the IntelligentLocationSearchTool."""
    tool = IntelligentLocationSearchTool()
    return tool.forward(query)

def search_dutch_address_pdok(address_query: str) -> dict:
    """Wrapper function for the SpecializedAddressSearchTool.""" 
    tool = SpecializedAddressSearchTool()
    return tool.forward(address_query)

# Test function
def test_intelligent_location_tools():
    """Test the intelligent location tools with various queries."""
    location_tool = IntelligentLocationSearchTool()
    address_tool = SpecializedAddressSearchTool()
    
    test_queries = [
        ("Amsterdam", "location"),
        ("Utrecht Centraal", "location"), 
        ("1012AB", "location"),
        ("Damrak 1, Amsterdam", "address"),
        ("Kloosterstraat 27, Ten Boer", "address"),
        ("Groningen", "location"),
        ("Rotterdam train station", "location")
    ]
    
    print("🧪 Testing Intelligent Location Tools")
    print("=" * 50)
    
    for query, tool_type in test_queries:
        print(f"\n🔍 Testing {tool_type}: '{query}'")
        
        if tool_type == "location":
            result = location_tool.forward(query)
        else:
            result = address_tool.forward(query)
        
        if result.get('error'):
            print(f"❌ Failed: {result['error']}")
        else:
            print(f"✅ Success: {result['name']}")
            print(f"   📍 Coordinates: {result['lat']:.6f}, {result['lon']:.6f}")
            print(f"   🎯 Precision: {result.get('precision', 'unknown')}")
            print(f"   🔍 Confidence: {result.get('confidence', 0):.1%}")

if __name__ == "__main__":
    test_intelligent_location_tools()