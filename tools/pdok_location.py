# pdok_location.py - PDOK Locatieserver API Integration Module

import requests
import json
from typing import Dict, List, Optional, Union
from smolagents import tool

class PDOKLocationService:
    """
    Service class for PDOK Locatieserver API integration.
    Handles all location search functionality for Dutch addresses and places.
    """
    
    def __init__(self):
        self.base_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"
        self.search_endpoint = f"{self.base_url}/search"
        self.lookup_endpoint = f"{self.base_url}/lookup"
        self.suggest_endpoint = f"{self.base_url}/suggest"
        self.user_agent = "PDOK-WebMap-Chat/1.0"
        
        # Available search types in PDOK Locatieserver
        self.search_types = {
            'adres': 'Address search',
            'gemeente': 'Municipality search', 
            'woonplaats': 'Residential place search',
            'weg': 'Street/road search (BAG openbare ruimte)',
            'postcode': 'Postal code search',
            'perceel': 'Land parcel search',
            'hectometerpaal': 'Hectometer post search'
        }
        
        # Major Dutch train stations with exact coordinates
        self.major_stations = {
            'amsterdam centraal': {'lat': 52.3791, 'lon': 4.8980, 'name': 'Amsterdam Centraal'},
            'amsterdam central': {'lat': 52.3791, 'lon': 4.8980, 'name': 'Amsterdam Centraal'},
            'amsterdam station': {'lat': 52.3791, 'lon': 4.8980, 'name': 'Amsterdam Centraal'},
            'amsterdam train station': {'lat': 52.3791, 'lon': 4.8980, 'name': 'Amsterdam Centraal'},
            'rotterdam centraal': {'lat': 51.9249, 'lon': 4.4690, 'name': 'Rotterdam Centraal'},
            'rotterdam central': {'lat': 51.9249, 'lon': 4.4690, 'name': 'Rotterdam Centraal'},
            'rotterdam station': {'lat': 51.9249, 'lon': 4.4690, 'name': 'Rotterdam Centraal'},
            'utrecht centraal': {'lat': 52.0897, 'lon': 5.1101, 'name': 'Utrecht Centraal'},
            'utrecht central': {'lat': 52.0897, 'lon': 5.1101, 'name': 'Utrecht Centraal'},
            'utrecht station': {'lat': 52.0897, 'lon': 5.1101, 'name': 'Utrecht Centraal'},
            'den haag centraal': {'lat': 52.0808, 'lon': 4.3240, 'name': 'Den Haag Centraal'},
            'the hague central': {'lat': 52.0808, 'lon': 4.3240, 'name': 'Den Haag Centraal'},
            'groningen station': {'lat': 53.2108, 'lon': 6.5665, 'name': 'Groningen'},
            'eindhoven centraal': {'lat': 51.4434, 'lon': 5.4815, 'name': 'Eindhoven Centraal'},
            'maastricht station': {'lat': 50.8514, 'lon': 5.7038, 'name': 'Maastricht'},
            'breda station': {'lat': 51.5955, 'lon': 4.7808, 'name': 'Breda'},
            'arnhem centraal': {'lat': 51.9851, 'lon': 5.9000, 'name': 'Arnhem Centraal'},
            'nijmegen station': {'lat': 51.8434, 'lon': 5.8520, 'name': 'Nijmegen'},
            'haarlem station': {'lat': 52.3874, 'lon': 4.6462, 'name': 'Haarlem'},
            'leiden centraal': {'lat': 52.1664, 'lon': 4.4816, 'name': 'Leiden Centraal'},
            'delft station': {'lat': 52.0067, 'lon': 4.3561, 'name': 'Delft'},
            'amersfoort centraal': {'lat': 52.1537, 'lon': 5.3756, 'name': 'Amersfoort Centraal'}
        }
    
    def search_location(self, query: str, search_types: str = "adres,woonplaats,gemeente,weg") -> Dict:
        """
        Search for Dutch locations using PDOK Locatieserver API.
        
        Args:
            query: Search query
            search_types: Comma-separated search types
            
        Returns:
            Location data with coordinates and details
        """
        try:
            print(f"🔍 PDOK Locatieserver search: '{query}'")
            
            # First try train station search if applicable
            if any(term in query.lower() for term in ['station', 'centraal', 'train']):
                station_result = self._search_train_station(query)
                if not station_result.get('error'):
                    return station_result
            
            # Prepare API parameters
            params = {
                'q': query,
                'rows': 10,
                'start': 0,
                'fl': '*',
                'fq': f'type:({search_types.replace(",", " OR ")})',
                'wt': 'json'
            }
            
            print(f"🌐 PDOK API request: {params}")
            
            # Make API request
            response = requests.get(
                self.search_endpoint,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('response', {}).get('docs'):
                return {"error": f"No results found for '{query}' in PDOK Locatieserver"}
            
            docs = data['response']['docs']
            print(f"📦 PDOK returned {len(docs)} results")
            
            # Choose best result
            best_result = self._choose_best_result(docs, query)
            
            if not best_result:
                return {"error": f"No suitable location found for '{query}'"}
            
            # Extract location data
            location_data = self._extract_location_data(best_result, query)
            
            print(f"✅ Selected: {location_data.get('name', 'Unknown')}")
            print(f"📍 Coordinates: {location_data.get('lat', 0):.6f}, {location_data.get('lon', 0):.6f}")
            
            return location_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ PDOK API request failed: {e}")
            return {"error": f"PDOK API request failed: {str(e)}"}
        except Exception as e:
            print(f"❌ Error in PDOK search: {e}")
            return {"error": f"Error searching PDOK: {str(e)}"}
    
    def _search_train_station(self, query: str) -> Dict:
        """Search for train stations using both direct lookup and API search."""
        try:
            query_normalized = query.lower().strip()
            
            # Direct lookup in major stations
            if query_normalized in self.major_stations:
                station = self.major_stations[query_normalized]
                return {
                    "name": station['name'],
                    "lat": station['lat'],
                    "lon": station['lon'],
                    "description": f"{station['name']} - Major Dutch railway station",
                    "place_type": "railway_station",
                    "source": "direct_lookup"
                }
            
            # Partial match in major stations
            for station_key, station_data in self.major_stations.items():
                if any(word in station_key for word in query_normalized.split()):
                    return {
                        "name": station_data['name'],
                        "lat": station_data['lat'],
                        "lon": station_data['lon'],
                        "description": f"{station_data['name']} - Major Dutch railway station",
                        "place_type": "railway_station",
                        "source": "partial_match"
                    }
            
            # API-based station search
            station_queries = self._generate_station_queries(query)
            
            for station_query in station_queries:
                params = {
                    'q': station_query,
                    'rows': 5,
                    'fl': '*',
                    'fq': 'type:(adres OR woonplaats OR weg)',
                    'wt': 'json'
                }
                
                response = requests.get(
                    self.search_endpoint,
                    params=params,
                    headers={"User-Agent": self.user_agent},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    docs = data.get('response', {}).get('docs', [])
                    
                    for doc in docs:
                        weergavenaam = doc.get('weergavenaam', '').lower()
                        straatnaam = doc.get('straatnaam', '').lower()
                        
                        if any(term in weergavenaam or term in straatnaam 
                               for term in ['station', 'centraal', 'stationsplein']):
                            result = self._extract_location_data(doc, query)
                            result['source'] = 'api_search'
                            return result
            
            return {"error": f"No train station found for '{query}'"}
            
        except Exception as e:
            return {"error": f"Error searching train station: {str(e)}"}
    
    def _generate_station_queries(self, query: str) -> List[str]:
        """Generate specific station search queries."""
        query_lower = query.lower()
        
        if 'amsterdam' in query_lower:
            return ["Amsterdam Centraal", "Stationsplein Amsterdam", "Amsterdam CS"]
        elif 'rotterdam' in query_lower:
            return ["Rotterdam Centraal", "Stationsplein Rotterdam", "Rotterdam CS"]
        elif 'utrecht' in query_lower:
            return ["Utrecht Centraal", "Stationsplein Utrecht", "Utrecht CS"]
        elif 'den haag' in query_lower or 'the hague' in query_lower:
            return ["Den Haag Centraal", "Den Haag HS", "Stationsplein Den Haag"]
        elif 'groningen' in query_lower:
            return ["Groningen", "Stationsplein Groningen"]
        else:
            return [f"{query} station", f"{query} centraal"]
    
    def _choose_best_result(self, docs: List[Dict], original_query: str) -> Optional[Dict]:
        """Choose the best result using scoring algorithm."""
        if not docs:
            return None
        
        query_lower = original_query.lower()
        scored_results = []
        
        for doc in docs:
            score = 0
            
            # Get key fields
            doc_type = doc.get('type', '').lower()
            weergavenaam = doc.get('weergavenaam', '').lower()
            straatnaam = doc.get('straatnaam', '').lower()
            woonplaatsnaam = doc.get('woonplaatsnaam', '').lower()
            gemeentenaam = doc.get('gemeentenaam', '').lower()
            
            # Type-based scoring
            type_scores = {'adres': 30, 'woonplaats': 25, 'gemeente': 20, 'weg': 15}
            score += type_scores.get(doc_type, 5)
            
            # Name matching scoring
            query_words = query_lower.split()
            for word in query_words:
                if word in weergavenaam: score += 20
                if word in straatnaam: score += 15
                if word in woonplaatsnaam: score += 10
                if word in gemeentenaam: score += 8
            
            # Station-specific scoring
            if any(term in query_lower for term in ['station', 'centraal', 'train']):
                if any(term in weergavenaam for term in ['station', 'centraal', 'stationsplein']):
                    score += 40
                if any(term in straatnaam for term in ['station', 'centraal', 'stationsplein']):
                    score += 35
            
            # Prefer results with coordinates
            if doc.get('centroide_ll'): score += 10
            
            # Type sorting preference
            typesortering = doc.get('typesortering', 0)
            if typesortering: score += float(typesortering) * 2
            
            scored_results.append((score, doc))
        
        # Sort and return best
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        print(f"🏆 PDOK Scored results:")
        for i, (score, result) in enumerate(scored_results[:3]):
            print(f"  {i+1}. Score: {score:.1f} - {result.get('weergavenaam', 'Unknown')}")
        
        return scored_results[0][1] if scored_results else None
    
    def _extract_location_data(self, doc: Dict, original_query: str) -> Dict:
        """Extract standardized location data from PDOK result."""
        try:
            # Extract coordinates
            centroide = doc.get('centroide_ll')
            lat, lon = 0.0, 0.0
            
            if centroide:
                if isinstance(centroide, str):
                    # Format: "POINT(lon lat)"
                    coords = centroide.replace('POINT(', '').replace(')', '').split()
                    if len(coords) == 2:
                        lon, lat = float(coords[0]), float(coords[1])
                elif isinstance(centroide, list) and len(centroide) == 2:
                    lon, lat = float(centroide[0]), float(centroide[1])
            
            # Build description
            weergavenaam = doc.get('weergavenaam', original_query)
            description_parts = []
            
            if doc.get('straatnaam') and doc.get('huisnummer'):
                description_parts.append(f"Address: {doc.get('straatnaam')} {doc.get('huisnummer')}")
            elif doc.get('straatnaam'):
                description_parts.append(f"Street: {doc.get('straatnaam')}")
            
            if doc.get('postcode'):
                description_parts.append(f"Postal code: {doc.get('postcode')}")
            if doc.get('woonplaatsnaam'):
                description_parts.append(f"Place: {doc.get('woonplaatsnaam')}")
            if doc.get('gemeentenaam'):
                description_parts.append(f"Municipality: {doc.get('gemeentenaam')}")
            if doc.get('provincienaam'):
                description_parts.append(f"Province: {doc.get('provincienaam')}")
            
            description = " | ".join(description_parts) if description_parts else weergavenaam
            
            return {
                "name": weergavenaam,
                "lat": lat,
                "lon": lon,
                "description": description,
                "place_type": doc.get('type', 'unknown'),
                "pdok_data": {
                    "id": doc.get('id'),
                    "type": doc.get('type'),
                    "gemeente": doc.get('gemeentenaam'),
                    "provincie": doc.get('provincienaam'),
                    "postcode": doc.get('postcode'),
                    "straatnaam": doc.get('straatnaam'),
                    "huisnummer": doc.get('huisnummer'),
                    "woonplaats": doc.get('woonplaatsnaam'),
                    "lookup_url": doc.get('lookup_url')
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
    
    def is_in_netherlands(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Netherlands boundaries."""
        return (50.7 <= lat <= 53.6) and (3.2 <= lon <= 7.3)

# Create global service instance
pdok_service = PDOKLocationService()

# Tool functions that your app.py can import
@tool
def find_location_coordinates(query: str) -> dict:
    """
    Enhanced location search using PDOK Locatieserver API for accurate Dutch locations.
    
    Args:
        query (str): Location query (e.g., 'Amsterdam train station', 'Kloosterstraat 27 Ten Boer')
    
    Returns:
        dict: Location data with coordinates and detailed information
    """
    try:
        print(f"🔍 Enhanced PDOK location search: '{query}'")
        
        # Use PDOK service for search
        result = pdok_service.search_location(query)
        
        if not result.get('error') and result.get('lat', 0) != 0 and result.get('lon', 0) != 0:
            # Validate coordinates are in Netherlands
            if pdok_service.is_in_netherlands(result['lat'], result['lon']):
                print(f"✅ PDOK found: {result.get('name')}")
                return result
            else:
                print(f"⚠️ Coordinates outside Netherlands: {result['lat']}, {result['lon']}")
        
        print(f"⚠️ PDOK search failed: {result.get('error', 'Unknown error')}")
        return {"error": f"Could not find Dutch location for '{query}'. {result.get('error', '')}"}
        
    except Exception as e:
        print(f"❌ Error in enhanced location search: {e}")
        return {"error": f"Location search error: {str(e)}"}

@tool
def search_dutch_address_pdok(address_query: str) -> dict:
    """
    Specialized search for Dutch addresses using PDOK Locatieserver.
    
    Args:
        address_query (str): Address query (e.g., 'Kloosterstraat 27 Ten Boer')
    
    Returns:
        dict: Detailed address information with coordinates
    """
    try:
        print(f"🏠 PDOK Address search: '{address_query}'")
        
        # Use address-specific search
        result = pdok_service.search_location(address_query, "adres")
        
        if not result.get('error'):
            print(f"✅ Found address: {result.get('name')}")
            return result
        else:
            return {"error": f"No address found for '{address_query}': {result.get('error')}"}
            
    except Exception as e:
        print(f"❌ Address search error: {e}")
        return {"error": f"Address search failed: {str(e)}"}

# Test function
def test_pdok_integration():
    """Test the PDOK integration with various queries."""
    test_queries = [
        "Amsterdam train station",
        "Rotterdam Centraal", 
        "Utrecht station",
        "Kloosterstraat 27 Ten Boer",
        "Damrak Amsterdam",
        "1012AB Amsterdam",
        "Den Haag Centraal",
        "Groningen station"
    ]
    
    print("🧪 Testing PDOK Location Integration")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        result = find_location_coordinates(query)
        
        if result.get('error'):
            print(f"❌ Failed: {result['error']}")
        else:
            print(f"✅ Success: {result['name']}")
            print(f"   📍 Coordinates: {result['lat']:.6f}, {result['lon']:.6f}")
            print(f"   📝 Description: {result['description']}")

if __name__ == "__main__":
    test_pdok_integration()