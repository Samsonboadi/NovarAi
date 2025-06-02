# tools/enhanced_pdok_intelligent_agent.py
import math
import re
import requests
import json
from datetime import datetime
from smolagents import Tool
from typing import Dict, List, Optional, Tuple, Union

class EnhancedPDOKIntelligentAgent(Tool):
    """
    Enhanced intelligent PDOK agent that automatically detects user intent and selects appropriate
    Dutch geospatial services and layers based on natural language requests.
    
    This tool can handle:
    - Buildings (panden) with size, age, and location filtering
    - Residential objects (verblijfsobjecten) with usage and area filtering  
    - Addresses and locations with precise geocoding
    - Administrative boundaries and parcels
    - Mixed queries combining multiple criteria
    
    The agent automatically:
    1. Analyzes the user's natural language request to detect intent
    2. Extracts location, filters, and parameters from the request
    3. Selects the appropriate PDOK service and layer
    4. Constructs proper API calls with spatial and attribute filtering
    5. Returns targeted results without random sampling
    """
    
    name = "enhanced_pdok_intelligent_agent"
    description = "Enhanced AI agent that understands natural language requests and automatically selects appropriate Dutch PDOK services for buildings, addresses, residential objects, and other geospatial data"
    inputs = {
        "user_request": {
            "type": "string", 
            "description": "Natural language request (e.g., 'find large buildings near Amsterdam', 'show verblijfsobject in Utrecht', 'what addresses are on Damrak')"
        },
        "max_features": {
            "type": "integer", 
            "description": "Maximum number of results to return (default: 50)", 
            "nullable": True
        },
        "search_radius_km": {
            "type": "number", 
            "description": "Search radius in kilometers (default: 5.0)", 
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        
        # Enhanced service catalog with better intent detection
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "layers": {
                    "bag:pand": {
                        "name": "Buildings (Panden)",
                        "description": "Building structures with construction year, area, and status",
                        "keywords": ["building", "buildings", "panden", "pand", "construction", "structure", "edifice"],
                        "filters": ["bouwjaar", "oppervlakte_min", "oppervlakte_max", "status"]
                    },
                    "bag:verblijfsobject": {
                        "name": "Residential Objects (Verblijfsobjecten)",
                        "description": "Residential and commercial units with usage and area",
                        "keywords": ["verblijfsobject", "residential", "apartment", "unit", "dwelling", "residence", "home"],
                        "filters": ["gebruiksdoel", "oppervlakte", "status"]
                    },
                    "bag:nummeraanduiding": {
                        "name": "Address Numbers",
                        "description": "House numbers and address information",
                        "keywords": ["address", "addresses", "nummeraanduiding", "house number", "postcode"],
                        "filters": ["huisnummer", "postcode"]
                    },
                    "bag:openbare_ruimte": {
                        "name": "Public Spaces",
                        "description": "Streets, squares, and public areas",
                        "keywords": ["street", "road", "square", "public space", "openbare ruimte"],
                        "filters": ["naam"]
                    }
                }
            },
            "bgt": {
                "name": "BGT - Large Scale Topography",
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                "layers": {
                    "bgt:gebouw_vlak": {
                        "name": "Building Surfaces",
                        "description": "Detailed building footprints and surfaces",
                        "keywords": ["building footprint", "building surface", "topography"],
                        "filters": ["bgt_type"]
                    }
                }
            }
        }
        
        # Intent classification patterns
        self.intent_patterns = {
            "building_search": {
                "keywords": ["building", "buildings", "panden", "pand", "structure", "construction"],
                "service": "bag",
                "layer": "bag:pand"
            },
            "residential_search": {
                "keywords": ["verblijfsobject", "residential", "apartment", "dwelling", "home", "unit", "residence"],
                "service": "bag", 
                "layer": "bag:verblijfsobject"
            },
            "address_search": {
                "keywords": ["address", "addresses", "house number", "postcode", "street number"],
                "service": "bag",
                "layer": "bag:nummeraanduiding"
            },
            "location_search": {
                "keywords": ["where is", "location of", "coordinates", "find location"],
                "service": "bag",
                "layer": "bag:nummeraanduiding"
            }
        }
        
        # Initialize coordinate transformers
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            print("✅ Enhanced PDOK Intelligent Agent initialized with coordinate transformers")
        except ImportError:
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
            print("⚠️ PyProj not available - coordinate transformation limited")
    
    def forward(self, user_request: str, max_features: int = 50, search_radius_km: float = 5.0) -> Dict:
        """
        Process a natural language request and return appropriate PDOK data.
        
        Args:
            user_request: Natural language request
            max_features: Maximum number of results to return
            search_radius_km: Search radius in kilometers
            
        Returns:
            Dictionary with text_description and geojson_data
        """
        try:
            print(f"🤖 Enhanced Agent Processing: {user_request}")
            
            # Step 1: Analyze the request and detect intent
            analysis = self._analyze_request_intent(user_request)
            print(f"🔍 Intent Analysis: {analysis}")
            
            # Step 2: Extract location from request
            location_info = self._extract_location(user_request)
            if location_info and not location_info.get('error'):
                print(f"📍 Location found: {location_info.get('name')} at {location_info.get('lat'):.6f}, {location_info.get('lon'):.6f}")
            else:
                print(f"⚠️ No specific location found in request")
            
            # Step 3: Build and execute PDOK query
            query_result = self._execute_pdok_query(analysis, location_info, max_features, search_radius_km)
            
            if query_result.get('error'):
                return {
                    "text_description": f"❌ Query failed: {query_result['error']}",
                    "geojson_data": [],
                    "error": query_result['error']
                }
            
            # Step 4: Process and format results
            processed_features = self._process_results(
                query_result.get('features', []), 
                analysis, 
                location_info
            )
            
            # Step 5: Generate response description
            description = self._generate_description(
                analysis, 
                processed_features, 
                location_info, 
                user_request
            )
            
            return {
                "text_description": description,
                "geojson_data": processed_features,
                "intent_detected": analysis.get('intent'),
                "location_found": location_info.get('name') if location_info else None,
                "service_used": f"{analysis.get('service')}/{analysis.get('layer')}"
            }
            
        except Exception as e:
            error_msg = f"Enhanced agent error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error processing request: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _analyze_request_intent(self, request: str) -> Dict:
        """
        Analyze the user request to detect intent and determine appropriate service/layer.
        
        Args:
            request: User's natural language request
            
        Returns:
            Dictionary with intent analysis results
        """
        request_lower = request.lower()
        
        # Default analysis structure
        analysis = {
            'intent': 'general_search',
            'service': 'bag',
            'layer': 'bag:pand',
            'data_type': 'buildings',
            'filters': {},
            'keywords_found': [],
            'confidence': 0.0
        }
        
        # Intent detection scoring
        intent_scores = {}
        
        for intent_name, intent_config in self.intent_patterns.items():
            score = 0
            keywords_found = []
            
            for keyword in intent_config['keywords']:
                if keyword in request_lower:
                    score += len(keyword)  # Longer keywords get higher scores
                    keywords_found.append(keyword)
            
            if score > 0:
                intent_scores[intent_name] = {
                    'score': score,
                    'keywords': keywords_found,
                    'config': intent_config
                }
        
        # Select best intent
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]['score'])
            best_config = intent_scores[best_intent]['config']
            
            analysis.update({
                'intent': best_intent,
                'service': best_config['service'],
                'layer': best_config['layer'], 
                'data_type': best_intent.replace('_search', ''),
                'keywords_found': intent_scores[best_intent]['keywords'],
                'confidence': intent_scores[best_intent]['score'] / len(request)
            })
        
        # Extract filters from request
        analysis['filters'] = self._extract_filters(request, analysis['layer'])
        
        print(f"🎯 Intent detected: {analysis['intent']} (confidence: {analysis['confidence']:.2f})")
        print(f"📋 Service selected: {analysis['service']} → {analysis['layer']}")
        
        return analysis
    
    def _extract_location(self, request: str) -> Optional[Dict]:
        """
        Extract location information from the request.
        
        Args:
            request: User's natural language request
            
        Returns:
            Location information dictionary or None
        """
        # Common location indicators
        location_patterns = [
            r'(?:near|in|at|around|close to|by)\s+([^,\s]+(?:\s+[^,\s]+)*)',
            r'(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:area|region|city)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            for match in matches:
                location_text = match.strip()
                
                # Skip common words that aren't locations
                skip_words = ['large', 'small', 'old', 'new', 'big', 'many', 'with', 'area', 'buildings']
                if any(word in location_text.lower() for word in skip_words):
                    continue
                
                # Try to geocode the location
                try:
                    from tools.pdok_location import find_location_coordinates
                    location_data = find_location_coordinates(location_text)
                    
                    if not location_data.get('error'):
                        print(f"✅ Location geocoded: {location_text} → {location_data.get('lat'):.6f}, {location_data.get('lon'):.6f}")
                        return location_data
                except Exception as e:
                    print(f"❌ Geocoding failed for '{location_text}': {e}")
                    continue
        
        return None
    
    def _extract_filters(self, request: str, layer: str) -> Dict:
        """
        Extract filters from the natural language request.
        
        Args:
            request: User's natural language request
            layer: Selected PDOK layer
            
        Returns:
            Dictionary of filters to apply
        """
        filters = {}
        request_lower = request.lower()
        
        # Area/size filters
        area_patterns = [
            r'area\s*[>≥]\s*(\d+)',
            r'larger\s+than\s+(\d+)\s*m²?',
            r'bigger\s+than\s+(\d+)\s*m²?',
            r'size\s*[>≥]\s*(\d+)',
            r'(\d+)\s*m²?\s+or\s+larger',
            r'minimum\s+(\d+)\s*m²?'
        ]
        
        for pattern in area_patterns:
            match = re.search(pattern, request_lower)
            if match:
                area_value = int(match.group(1))
                if layer == 'bag:pand':
                    filters['min_area'] = area_value
                elif layer == 'bag:verblijfsobject':
                    filters['min_oppervlakte'] = area_value
                print(f"📏 Area filter detected: ≥ {area_value}m²")
                break
        
        # Year/age filters
        year_patterns = [
            r'built\s+before\s+(\d{4})',
            r'older\s+than\s+(\d+)\s+years?',
            r'before\s+(\d{4})',
            r'pre[-\s](\d{4})',
            r'historic',
            r'ancient',
            r'old'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, request_lower)
            if match:
                if pattern in ['historic', 'ancient', 'old']:
                    filters['max_year'] = 1950  # Historic buildings
                    print(f"🏛️ Historic building filter applied (before 1950)")
                else:
                    year_value = int(match.group(1))
                    if 'older than' in pattern:
                        filters['max_year'] = 2024 - year_value
                    else:
                        filters['max_year'] = year_value
                    print(f"📅 Year filter detected: ≤ {filters.get('max_year')}")
                break
        
        # Usage type filters (for verblijfsobject)
        if layer == 'bag:verblijfsobject':
            usage_patterns = {
                'residential': ['woonfunctie'],
                'commercial': ['winkelfunctie', 'kantoorfunctie'],
                'office': ['kantoorfunctie'],
                'shop': ['winkelfunctie'],
                'industrial': ['industriefunctie']
            }
            
            for usage_type, pdok_values in usage_patterns.items():
                if usage_type in request_lower:
                    filters['gebruiksdoel'] = pdok_values[0]
                    print(f"🏢 Usage filter detected: {usage_type}")
                    break
        
        return filters
    
    def _execute_pdok_query(self, analysis: Dict, location_info: Optional[Dict], 
                           max_features: int, search_radius_km: float) -> Dict:
        """
        Execute the PDOK WFS query based on analysis results.
        
        Args:
            analysis: Intent analysis results
            location_info: Location information
            max_features: Maximum features to return
            search_radius_km: Search radius in kilometers
            
        Returns:
            Query results with features or error
        """
        try:
            service_config = self.services[analysis['service']]
            service_url = service_config['url']
            layer_name = analysis['layer']
            
            # Build WFS parameters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'count': min(max_features * 3, 1000),  # Get extra for filtering
                'srsName': 'EPSG:28992'
            }
            
            # Add spatial filter if location is provided
            if location_info and not location_info.get('error'):
                bbox = self._create_spatial_bbox(location_info, search_radius_km)
                if bbox:
                    params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
                    print(f"🗺️ Spatial filter applied: {search_radius_km}km radius")
            
            # Add attribute filters
            cql_filters = self._build_cql_filters(analysis['filters'], layer_name)
            if cql_filters:
                params['cql_filter'] = cql_filters
                print(f"🔍 Attribute filters applied: {cql_filters}")
            
            print(f"🚀 Executing PDOK query: {service_url}")
            print(f"📋 Layer: {layer_name}")
            
            # Make the request
            response = requests.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"📦 PDOK returned {len(features)} features")
            
            return {"features": features}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"PDOK request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Query execution error: {str(e)}"}
    
    def _create_spatial_bbox(self, location_info: Dict, radius_km: float) -> Optional[List[float]]:
        """
        Create a bounding box around the location.
        
        Args:
            location_info: Location information with lat/lon
            radius_km: Radius in kilometers
            
        Returns:
            Bounding box coordinates [minx, miny, maxx, maxy] or None
        """
        if not self.transformer_to_rd:
            return None
            
        try:
            lat, lon = location_info['lat'], location_info['lon']
            center_x, center_y = self.transformer_to_rd.transform(lon, lat)
            
            radius_m = radius_km * 1000
            
            return [
                center_x - radius_m,
                center_y - radius_m, 
                center_x + radius_m,
                center_y + radius_m
            ]
            
        except Exception as e:
            print(f"❌ Error creating spatial bbox: {e}")
            return None
    
    def _build_cql_filters(self, filters: Dict, layer_name: str) -> Optional[str]:
        """
        Build CQL filter string from extracted filters.
        
        Args:
            filters: Dictionary of filters
            layer_name: PDOK layer name
            
        Returns:
            CQL filter string or None
        """
        cql_parts = []
        
        # Area filters
        if filters.get('min_area') and layer_name == 'bag:pand':
            cql_parts.append(f"oppervlakte_min >= {filters['min_area']}")
        
        if filters.get('min_oppervlakte') and layer_name == 'bag:verblijfsobject':
            cql_parts.append(f"oppervlakte >= {filters['min_oppervlakte']}")
        
        # Year filters
        if filters.get('max_year') and layer_name == 'bag:pand':
            cql_parts.append(f"bouwjaar <= {filters['max_year']}")
        
        # Usage filters
        if filters.get('gebruiksdoel') and layer_name == 'bag:verblijfsobject':
            cql_parts.append(f"gebruiksdoel = '{filters['gebruiksdoel']}'")
        
        return " AND ".join(cql_parts) if cql_parts else None
    
    def _process_results(self, features: List[Dict], analysis: Dict, 
                        location_info: Optional[Dict]) -> List[Dict]:
        """
        Process raw PDOK features into the expected format.
        
        Args:
            features: Raw features from PDOK
            analysis: Intent analysis results
            location_info: Location information for distance calculation
            
        Returns:
            List of processed features
        """
        processed = []
        
        for i, feature in enumerate(features):
            try:
                props = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                # Calculate centroid
                centroid = self._get_centroid_wgs84(geometry)
                if not centroid:
                    continue
                
                lat, lon = centroid
                
                # Calculate distance if location provided
                distance_km = None
                if location_info and not location_info.get('error'):
                    distance_km = self._calculate_distance(
                        location_info['lat'], location_info['lon'], lat, lon
                    )
                
                # Apply additional filtering
                if not self._passes_additional_filters(props, analysis['filters']):
                    continue
                
                # Create feature name and description
                feature_data = self._create_feature_data(
                    props, analysis, i, distance_km
                )
                
                # Convert geometry to WGS84
                wgs84_geom = self._convert_geometry_to_wgs84(geometry)
                
                processed_feature = {
                    "name": feature_data['name'],
                    "lat": float(lat),
                    "lon": float(lon),
                    "description": feature_data['description'],
                    "geometry": wgs84_geom,
                    "properties": {
                        **props,
                        "centroid_lat": float(lat),
                        "centroid_lon": float(lon),
                        "distance_km": distance_km,
                        "data_type": analysis['data_type'],
                        "intent": analysis['intent']
                    }
                }
                
                processed.append(processed_feature)
                
            except Exception as e:
                print(f"❌ Error processing feature {i+1}: {e}")
                continue
        
        # Sort by distance if location provided
        if location_info and not location_info.get('error'):
            processed.sort(key=lambda x: x['properties'].get('distance_km', 999))
        
        return processed
    
    def _passes_additional_filters(self, props: Dict, filters: Dict) -> bool:
        """
        Check if feature passes additional post-query filters.
        
        Args:
            props: Feature properties
            filters: Filter criteria
            
        Returns:
            True if feature passes all filters
        """
        # Additional area filtering for precision
        if filters.get('min_area'):
            area = props.get('oppervlakte_min') or props.get('oppervlakte_max', 0)
            if area < filters['min_area']:
                return False
        
        if filters.get('min_oppervlakte'):
            area = props.get('oppervlakte', 0)
            if area < filters['min_oppervlakte']:
                return False
        
        # Additional year filtering
        if filters.get('max_year'):
            year = props.get('bouwjaar')
            if year and year > filters['max_year']:
                return False
        
        return True
    
    def _create_feature_data(self, props: Dict, analysis: Dict, 
                           index: int, distance_km: Optional[float]) -> Dict:
        """
        Create feature name and description based on data type.
        
        Args:
            props: Feature properties
            analysis: Intent analysis results
            index: Feature index
            distance_km: Distance from search location
            
        Returns:
            Dictionary with name and description
        """
        feature_id = props.get('identificatie', f'Feature_{index+1}')
        data_type = analysis['data_type']
        
        # Create name
        if data_type == 'buildings':
            name = f"Building {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
            if props.get('bouwjaar'):
                name += f" ({props['bouwjaar']})"
        elif data_type == 'residential':
            name = f"Residence {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
        elif data_type == 'address':
            street = props.get('openbare_ruimte', '')
            number = props.get('huisnummer', '')
            name = f"{street} {number}".strip() or f"Address {feature_id[-6:]}"
        else:
            name = f"{data_type.title()} {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
        
        # Create description
        desc_parts = []
        
        if distance_km is not None:
            desc_parts.append(f"Distance: {distance_km:.3f}km")
        
        if data_type == 'buildings':
            if props.get('bouwjaar'):
                age = 2024 - props['bouwjaar']
                desc_parts.append(f"Built: {props['bouwjaar']} ({age} years old)")
            
            area = props.get('oppervlakte_min') or props.get('oppervlakte_max')
            if area:
                desc_parts.append(f"Area: {area}m²")
            
            if props.get('status'):
                desc_parts.append(f"Status: {props['status']}")
                
        elif data_type == 'residential':
            if props.get('gebruiksdoel'):
                desc_parts.append(f"Use: {props['gebruiksdoel']}")
            
            if props.get('oppervlakte'):
                desc_parts.append(f"Area: {props['oppervlakte']}m²")
            
            if props.get('status'):
                desc_parts.append(f"Status: {props['status']}")
                
        elif data_type == 'address':
            if props.get('postcode'):
                desc_parts.append(f"Postcode: {props['postcode']}")
            
            if props.get('woonplaats'):
                desc_parts.append(f"City: {props['woonplaats']}")
        
        description = " | ".join(desc_parts) if desc_parts else f"{data_type.title()} information"
        
        return {"name": name, "description": description}
    
    def _generate_description(self, analysis: Dict, features: List[Dict], 
                            location_info: Optional[Dict], user_request: str) -> str:
        """
        Generate a comprehensive text description of the results.
        
        Args:
            analysis: Intent analysis results
            features: Processed features
            location_info: Location information
            user_request: Original user request
            
        Returns:
            Formatted text description
        """
        if not features:
            location_text = f" in {location_info['name']}" if location_info else ""
            return f"❌ No {analysis['data_type']} found{location_text} matching your criteria: '{user_request}'"
        
        text_parts = []
        
        # Header
        intent_display = analysis['intent'].replace('_', ' ').title()
        location_text = f" in {location_info['name']}" if location_info else ""
        text_parts.append(f"## {intent_display} Results{location_text}")
        
        # Summary
        service_name = self.services[analysis['service']]['name']
        layer_name = self.services[analysis['service']]['layers'][analysis['layer']]['name']
        
        text_parts.append(f"\nI found **{len(features)} {analysis['data_type']}**{location_text} using {service_name} ({layer_name}).")
        
        # Intent and confidence
        if analysis['confidence'] > 0.5:
            text_parts.append(f"**Intent detected**: {intent_display} (confidence: {analysis['confidence']:.1%})")
        
        # Filters applied
        if analysis['filters']:
            filter_desc = []
            for filter_key, filter_value in analysis['filters'].items():
                if 'area' in filter_key or 'oppervlakte' in filter_key:
                    filter_desc.append(f"area ≥ {filter_value}m²")
                elif 'year' in filter_key:
                    filter_desc.append(f"built ≤ {filter_value}")
                elif 'gebruiksdoel' in filter_key:
                    filter_desc.append(f"usage: {filter_value}")
            
            if filter_desc:
                text_parts.append(f"**Filters applied**: {', '.join(filter_desc)}")
        
        # Location details
        if location_info and not location_info.get('error'):
            text_parts.append(f"**Search center**: {location_info['lat']:.6f}°N, {location_info['lon']:.6f}°E")
        
        # Sample results
        sample_count = min(5, len(features))
        text_parts.append(f"\n**Sample {analysis['data_type']} found**:")
        
        for feature in features[:sample_count]:
            text_parts.append(f"* **{feature['name']}** - {feature['description']}")
        
        if len(features) > sample_count:
            text_parts.append(f"... and {len(features) - sample_count} more")
        
        # Technical details
        text_parts.append(f"\n**Technical**: Enhanced intelligent agent automatically selected {analysis['service']}/{analysis['layer']} based on intent analysis of your request.")
        
        # Map reference
        text_parts.append(f"\nAll **{len(features)} {analysis['data_type']}** are displayed on the map with detailed information.")
        
        return "\n".join(text_parts)
    
    def _get_centroid_wgs84(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """Calculate centroid in WGS84 coordinates."""
        try:
            if geometry['type'] == 'Point':
                coords = geometry['coordinates']
                if self.transformer_to_wgs84:
                    wgs84 = self.transformer_to_wgs84.transform(coords[0], coords[1])
                    return wgs84[1], wgs84[0]  # lat, lon
                return coords[1], coords[0]
                
            elif geometry['type'] == 'Polygon':
                coords = geometry['coordinates'][0]
                if coords:
                    avg_x = sum(c[0] for c in coords) / len(coords)
                    avg_y = sum(c[1] for c in coords) / len(coords)
                    
                    if self.transformer_to_wgs84:
                        wgs84 = self.transformer_to_wgs84.transform(avg_x, avg_y)
                        return wgs84[1], wgs84[0]  # lat, lon
                    return avg_y, avg_x
            
            return None
        except Exception:
            return None
    
    def _convert_geometry_to_wgs84(self, geometry: Dict) -> Dict:
        """Convert geometry from RD New to WGS84."""
        try:
            if not self.transformer_to_wgs84:
                return geometry
            
            if geometry['type'] == 'Point':
                wgs84 = self.transformer_to_wgs84.transform(geometry['coordinates'][0], geometry['coordinates'][1])
                return {'type': 'Point', 'coordinates': [wgs84[0], wgs84[1]]}
            
            elif geometry['type'] == 'Polygon':
                wgs84_coords = []
                for ring in geometry['coordinates']:
                    wgs84_ring = []
                    for coord in ring:
                        wgs84 = self.transformer_to_wgs84.transform(coord[0], coord[1])
                        wgs84_ring.append([wgs84[0], wgs84[1]])
                    wgs84_coords.append(wgs84_ring)
                return {'type': 'Polygon', 'coordinates': wgs84_coords}
            
            return geometry
        except Exception:
            return geometry
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        try:
            R = 6371  # Earth's radius in kilometers
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                math.cos(lat1_rad) * math.cos(lat2_rad) * 
                math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        except Exception:
            return 999.0


class SmartServiceDiscoveryTool(Tool):
    """
    Smart service discovery tool that analyzes user requests to recommend
    the most appropriate PDOK services and provides usage examples.
    """
    
    name = "smart_pdok_service_discovery"
    description = "Intelligent service discovery that analyzes user requests and recommends appropriate PDOK services with usage examples and availability status"
    inputs = {
        "user_query": {
            "type": "string", 
            "description": "User's request or question about PDOK services (e.g., 'I need building data', 'what services are available for addresses')"
        },
        "check_availability": {
            "type": "boolean", 
            "description": "Whether to check real-time service availability (default: true)", 
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        
        self.service_catalog = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "description": "Authoritative Dutch building and address database",
                "use_cases": [
                    "Finding buildings by location and age",
                    "Searching for addresses and house numbers", 
                    "Analyzing residential and commercial properties",
                    "Getting building construction details"
                ],
                "layers": {
                    "bag:pand": {
                        "name": "Buildings (Panden)",
                        "keywords": ["building", "construction", "structure", "pand"],
                        "example_query": "Find large buildings near Amsterdam built before 1950"
                    },
                    "bag:verblijfsobject": {
                        "name": "Residential Objects",
                        "keywords": ["residence", "apartment", "dwelling", "verblijfsobject"],
                        "example_query": "Show residential properties in Utrecht with area > 100m²"
                    },
                    "bag:nummeraanduiding": {
                        "name": "Address Numbers",
                        "keywords": ["address", "house number", "postcode"],
                        "example_query": "Find all addresses on Damrak street in Amsterdam"
                    }
                }
            }
        }
    
    def forward(self, user_query: str, check_availability: bool = True) -> Dict:
        """
        Analyze user query and provide smart service recommendations.
        
        Args:
            user_query: User's request or question
            check_availability: Whether to check service availability
            
        Returns:
            Service recommendations and usage examples
        """
        try:
            print(f"🔍 Smart Discovery analyzing: {user_query}")
            
            # Analyze query intent
            analysis = self._analyze_query_intent(user_query)
            
            # Get service recommendations
            recommendations = self._get_service_recommendations(analysis)
            
            # Check availability if requested
            if check_availability:
                availability = self._check_service_availability()
                for service_key in recommendations['services'].keys():
                    recommendations['services'][service_key]['availability'] = availability.get(service_key, {})
            
            # Generate usage examples
            examples = self._generate_usage_examples(analysis, recommendations)
            
            return {
                "query_analysis": analysis,
                "recommended_services": recommendations,
                "usage_examples": examples,
                "total_services_available": len(self.service_catalog),
                "discovery_confidence": analysis.get('confidence', 0.0)
            }
            
        except Exception as e:
            return {"error": f"Smart discovery error: {str(e)}"}
    
    def _analyze_query_intent(self, query: str) -> Dict:
        """Analyze the user's query to understand their intent."""
        query_lower = query.lower()
        
        analysis = {
            'intent_type': 'general',
            'data_types': [],
            'keywords_found': [],
            'confidence': 0.0,
            'spatial_scope': None,
            'specific_needs': []
        }
        
        # Intent detection patterns
        intent_patterns = {
            'service_discovery': ['what services', 'available services', 'what can i', 'show me services'],
            'building_search': ['building', 'buildings', 'panden', 'construction'],
            'address_search': ['address', 'addresses', 'house number', 'postcode'],
            'residential_search': ['residential', 'verblijfsobject', 'apartment', 'dwelling'],
            'data_exploration': ['data available', 'what data', 'explore data']
        }
        
        # Score intents
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent] = score
                analysis['keywords_found'].extend([k for k in keywords if k in query_lower])
        
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
            analysis['intent_type'] = best_intent
            analysis['confidence'] = intent_scores[best_intent] / len(query.split())
        
        # Extract data types
        for service_key, service_config in self.service_catalog.items():
            for layer_key, layer_config in service_config['layers'].items():
                for keyword in layer_config['keywords']:
                    if keyword in query_lower:
                        analysis['data_types'].append(layer_key)
        
        # Extract spatial scope
        location_indicators = ['near', 'in', 'around', 'at', 'amsterdam', 'utrecht', 'rotterdam', 'groningen']
        for indicator in location_indicators:
            if indicator in query_lower:
                analysis['spatial_scope'] = 'location_specific'
                break
        
        return analysis
    
    def _get_service_recommendations(self, analysis: Dict) -> Dict:
        """Get service recommendations based on analysis."""
        recommendations = {
            'services': {},
            'primary_recommendation': None,
            'reasoning': []
        }
        
        # If specific data types detected, recommend those services
        if analysis['data_types']:
            for data_type in analysis['data_types']:
                service_key = data_type.split(':')[0]
                if service_key in self.service_catalog:
                    service_config = self.service_catalog[service_key]
                    recommendations['services'][service_key] = {
                        **service_config,
                        'recommended_layers': [data_type],
                        'relevance_score': 1.0
                    }
                    recommendations['reasoning'].append(f"Detected interest in {data_type}")
        
        # If no specific types, recommend all services
        else:
            for service_key, service_config in self.service_catalog.items():
                recommendations['services'][service_key] = {
                    **service_config,
                    'recommended_layers': list(service_config['layers'].keys()),
                    'relevance_score': 0.5
                }
        
        # Set primary recommendation
        if recommendations['services']:
            primary_key = max(recommendations['services'].keys(), 
                            key=lambda x: recommendations['services'][x]['relevance_score'])
            recommendations['primary_recommendation'] = primary_key
        
        return recommendations
    
    def _check_service_availability(self) -> Dict:
        """Check real-time availability of PDOK services."""
        availability = {}
        
        for service_key, service_config in self.service_catalog.items():
            try:
                params = {
                    'service': 'WFS',
                    'version': '2.0.0', 
                    'request': 'GetCapabilities'
                }
                
                response = requests.get(service_config['url'], params=params, timeout=10)
                
                if response.status_code == 200:
                    availability[service_key] = {
                        'available': True,
                        'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                        'status': 'operational'
                    }
                else:
                    availability[service_key] = {
                        'available': False,
                        'status': f'HTTP {response.status_code}',
                        'error': 'Service unavailable'
                    }
                    
            except Exception as e:
                availability[service_key] = {
                    'available': False,
                    'status': 'error',
                    'error': str(e)
                }
        
        return availability
    
    def _generate_usage_examples(self, analysis: Dict, recommendations: Dict) -> List[Dict]:
        """Generate contextual usage examples."""
        examples = []
        
        for service_key, service_info in recommendations['services'].items():
            for layer_key, layer_config in service_info['layers'].items():
                example = {
                    'service': service_key,
                    'layer': layer_key,
                    'example_query': layer_config.get('example_query', f"Search for {layer_config['name'].lower()}"),
                    'description': f"Use {layer_config['name']} to {layer_config['example_query'].lower()}"
                }
                examples.append(example)
        
        return examples[:5]  # Limit to 5 examples