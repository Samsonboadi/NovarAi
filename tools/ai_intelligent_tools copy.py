# tools/ai_intelligent_tools.py - Tools for AI to use (not for intent detection)

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple

class PDOKServiceDiscoveryTool(Tool):
    """
    Enhanced service discovery tool that the AI can use to understand what endpoints are available.
    The AI will call this to learn about PDOK services before making decisions.
    """
    
    name = "discover_pdok_services"
    description = """Discover available PDOK WFS services and their capabilities.

This tool helps the AI understand what PDOK services and layers are available.
The AI should use this to learn about available endpoints before constructing queries.

Returns information about:
- Available WFS services (BAG, BGT, BRK, CBS, Cadastral Map, Natura 2000)
- Layers within each service
- Capabilities and feature types
- Service availability status
- Enhanced guidance for service selection

The AI can then use this information to select appropriate services and construct API calls."""
    
    inputs = {
        "service_name": {
            "type": "string", 
            "description": "Specific service to check (bag, bgt, brk, cbs, cadastral, natura2000) or 'all' for all services",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # Enhanced PDOK services for the AI to discover
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "description": "Dutch Buildings and Addresses Database",
                "typical_use": "Buildings (panden), addresses (nummeraanduiding), residential objects (verblijfsobject)",
                "keywords": ["buildings", "addresses", "residential", "properties"]
            },
            "bgt": {
                "name": "BGT - Large Scale Topography", 
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                "description": "Detailed topographic features",
                "typical_use": "Building surfaces, roads, water features, land use",
                "keywords": ["topography", "roads", "water", "land use", "surfaces"]
            },
            "brk": {
                "name": "BRK - Cadastral Registry",
                "url": "https://service.pdok.nl/lv/brk/wfs/v2_0",
                "description": "Land parcels and ownership information",
                "typical_use": "Land parcels (perceel), ownership rights (zakelijkrecht)",
                "keywords": ["ownership", "rights", "parcels", "cadastral registry"]
            },
            "cbs": {
                "name": "CBS - Statistics Netherlands",
                "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
                "description": "Administrative boundaries and statistics",
                "typical_use": "Municipalities (gemeenten), districts (wijken), neighborhoods (buurten)",
                "keywords": ["statistics", "boundaries", "municipalities", "districts", "neighborhoods"]
            },
            "cadastral": {
                "name": "Cadastral Map - Kadastrale Kaart",
                "url": "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0",
                "description": "Overview of cadastral parcel locations in the Netherlands. Functions as a link between terrain and registration, often serves as a reference for users.",
                "typical_use": "Cadastral parcels (kadastrale percelen), cadastral boundaries, building outlines, address ranges, public space names",
                "keywords": ["cadastral", "parcels", "boundaries", "kadaster", "terrain", "reference", "quality labels"]
            },
            "natura2000": {
                "name": "Natura 2000 - Protected Nature Areas",
                "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
                "description": "Natura 2000 is the coherent network of protected natural areas in the European Union consisting of Bird Directive and Habitat Directive areas.",
                "typical_use": "Protected nature areas, Bird Directive areas, Habitat Directive areas, nature monuments",
                "keywords": ["natura2000", "protected areas", "nature", "habitat", "bird directive", "conservation", "environment"]
            }
        }
    
    def forward(self, service_name: Optional[str] = "all") -> Dict:
        """Discover PDOK services for AI decision making."""
        try:
            print(f"🔍 Discovering PDOK services: {service_name}")
            
            if service_name == "all" or service_name is None:
                discovered_services = {}
                
                for key, config in self.services.items():
                    print(f"📡 Checking {key}...")
                    capabilities = self._get_capabilities(config["url"])
                    
                    discovered_services[key] = {
                        **config,
                        "capabilities": capabilities,
                        "available": not capabilities.get('error'),
                        "layers": capabilities.get('layers', [])
                    }
                
                return {
                    "services": discovered_services,
                    "summary": f"Discovered {len(discovered_services)} PDOK services",
                    "ai_guidance": {
                        "for_buildings": "Use 'bag' service with layers like 'bag:pand'",
                        "for_addresses": "Use 'bag' service with 'bag:nummeraanduiding'",
                        "for_parcels": "Use 'brk' service with 'brk:perceel' or 'cadastral' for visual parcel boundaries",
                        "for_boundaries": "Use 'cbs' service for administrative boundaries",
                        "for_cadastral_map": "Use 'cadastral' service for detailed cadastral parcel visualization and reference",
                        "for_nature_protection": "Use 'natura2000' service for protected natural areas and conservation zones",
                        "for_environmental_analysis": "Combine 'natura2000' with other services for environmental impact assessment"
                    },
                    "service_selection_tips": {
                        "cadastral_vs_brk": "Use 'cadastral' for visual/mapping purposes, 'brk' for ownership/legal information",
                        "nature_queries": "Use 'natura2000' for protected areas, environmental regulations, and conservation planning",
                        "reference_mapping": "Use 'cadastral' as a base layer for overlaying other spatial information"
                    }
                }
            
            elif service_name in self.services:
                config = self.services[service_name]
                capabilities = self._get_capabilities(config["url"])
                
                return {
                    "service": {
                        **config,
                        "capabilities": capabilities,
                        "available": not capabilities.get('error'),
                        "layers": capabilities.get('layers', [])
                    },
                    "usage_recommendations": self._get_usage_recommendations(service_name)
                }
            
            else:
                available_services = list(self.services.keys())
                return {
                    "error": f"Unknown service: {service_name}. Available services: {available_services}",
                    "available_services": available_services
                }
                
        except Exception as e:
            return {"error": f"Service discovery error: {str(e)}"}
    
    def _get_capabilities(self, service_url: str) -> Dict:
        """Get WFS capabilities for a service with enhanced parsing."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            response = requests.get(service_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Parse XML to extract layer info
            root = ET.fromstring(response.content)
            
            # Extract service information
            service_info = self._extract_service_info(root)
            
            layers = []
            for feature_type in root.iter():
                if feature_type.tag.endswith('FeatureType'):
                    name_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Name')
                    title_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Title')
                    abstract_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Abstract')
                    
                    if name_elem is not None:
                        layer_info = {
                            "name": name_elem.text,
                            "title": title_elem.text if title_elem is not None else name_elem.text,
                            "description": abstract_elem.text if abstract_elem is not None else ""
                        }
                        layers.append(layer_info)
            
            return {
                "layers": layers,
                "layer_count": len(layers),
                "service_operational": True,
                "service_info": service_info
            }
            
        except Exception as e:
            return {"error": f"Could not get capabilities: {str(e)}"}
    
    def _extract_service_info(self, root) -> Dict:
        """Extract additional service information from capabilities XML."""
        service_info = {}
        
        try:
            # Extract service identification
            service_id = root.find('.//{http://www.opengis.net/ows/1.1}ServiceIdentification')
            if service_id is not None:
                title_elem = service_id.find('.//{http://www.opengis.net/ows/1.1}Title')
                abstract_elem = service_id.find('.//{http://www.opengis.net/ows/1.1}Abstract')
                
                if title_elem is not None:
                    service_info['title'] = title_elem.text
                if abstract_elem is not None:
                    service_info['abstract'] = abstract_elem.text
                
                # Extract keywords
                keywords = []
                for keyword_elem in service_id.findall('.//{http://www.opengis.net/ows/1.1}Keyword'):
                    if keyword_elem.text:
                        keywords.append(keyword_elem.text)
                service_info['keywords'] = keywords
        
        except Exception as e:
            service_info['extraction_error'] = str(e)
        
        return service_info
    
    def _get_usage_recommendations(self, service_name: str) -> Dict:
        """Provide specific usage recommendations for each service."""
        recommendations = {
            "bag": {
                "best_for": ["Finding building information", "Address lookup", "Property analysis"],
                "common_layers": ["bag:pand", "bag:nummeraanduiding", "bag:verblijfsobject"],
                "tips": "Use spatial filters for location-based queries"
            },
            "bgt": {
                "best_for": ["Detailed topographic analysis", "Infrastructure mapping", "Land use studies"],
                "common_layers": ["Various topographic feature layers"],
                "tips": "High detail level - use appropriate scale for performance"
            },
            "brk": {
                "best_for": ["Ownership research", "Legal parcel information", "Property rights"],
                "common_layers": ["brk:perceel", "brk:zakelijkrecht"],
                "tips": "Contains legal/ownership data - complement with cadastral for visualization"
            },
            "cbs": {
                "best_for": ["Administrative boundaries", "Statistical analysis", "Demographic studies"],
                "common_layers": ["Municipality, district, and neighborhood layers"],
                "tips": "Good for regional analysis and administrative context"
            },
            "cadastral": {
                "best_for": ["Visual parcel mapping", "Reference base layer", "Cadastral visualization"],
                "common_layers": ["Cadastral parcels", "Boundaries", "Building outlines"],
                "tips": "Ideal as base layer for other spatial data - high quality reference mapping"
            },
            "natura2000": {
                "best_for": ["Environmental protection analysis", "Conservation planning", "Protected area identification"],
                "common_layers": ["Protected nature areas", "Habitat directive areas", "Bird directive areas"],
                "tips": "Essential for environmental impact assessments and conservation projects"
            }
        }
        
        return recommendations.get(service_name, {"best_for": [], "common_layers": [], "tips": ""})


class LocationSearchTool(Tool):
    """
    Location search tool for the AI to find coordinates.
    The AI should use this when it identifies location mentions in user queries.
    """
    
    name = "search_location_coordinates"
    description = """Find coordinates for Dutch locations.

The AI should use this tool when it identifies location mentions in user queries.
This tool can find coordinates for:
- Cities and municipalities (Amsterdam, Groningen, Utrecht)
- Specific addresses (Damrak 1 Amsterdam, Leonard Springerlaan 37 Groningen)
- Landmarks (Amsterdam Centraal station, Groningen train station)
- Postal codes (1012AB, 9711AB)

The AI can then use the returned coordinates to create spatial filters for PDOK queries."""
    
    inputs = {
        "location_query": {
            "type": "string",
            "description": "Location to search for (address, city, landmark, postal code)"
        }
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, location_query: str) -> Dict:
        """Search for location coordinates."""
        try:
            # Try to use the enhanced location tool if available
            try:
                from tools.enhanced_pdok_location_tool import find_location_coordinates
                result = find_location_coordinates(location_query)
                print(f"📍 Location found: {result.get('name', 'Unknown')} at {result.get('lat', 0):.6f}, {result.get('lon', 0):.6f}")
                return result
            except ImportError:
                # Basic fallback using PDOK Locatieserver
                return self._basic_location_search(location_query)
                
        except Exception as e:
            return {"error": f"Location search error: {str(e)}"}
    
    def _basic_location_search(self, query: str) -> Dict:
        """Basic location search using PDOK Locatieserver."""
        try:
            url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
            params = {
                'q': query,
                'rows': 5,
                'fl': 'weergavenaam,centroide_ll,score',
                'fq': 'type:(adres OR woonplaats OR gemeente)',
                'wt': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if not docs:
                return {"error": f"No location found for: {query}"}
            
            # Use best result
            best = docs[0]
            name = best.get('weergavenaam', query)
            centroide = best.get('centroide_ll', '')
            
            # Parse coordinates from POINT(lon lat) format
            if centroide and 'POINT(' in centroide:
                coords = centroide.replace('POINT(', '').replace(')', '').split()
                if len(coords) == 2:
                    lon, lat = float(coords[0]), float(coords[1])
                    
                    return {
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "description": f"Location: {name}",
                        "source": "pdok_locatieserver"
                    }
            
            return {"error": f"Could not parse coordinates for: {query}"}
            
        except Exception as e:
            return {"error": f"Basic location search failed: {str(e)}"}


class PDOKDataRequestTool(Tool):
    """
    PDOK data request tool for the AI to make WFS requests.
    The AI should construct the appropriate parameters based on its analysis.
    """
    
    name = "request_pdok_data"
    description = """Make WFS requests to PDOK services.

The AI should use this tool after:
1. Analyzing the user query to understand what data is needed
2. Using discover_pdok_services to understand available endpoints
3. Using search_location_coordinates to get coordinates if needed
4. Determining the appropriate service URL, layer, and filters

The AI constructs the parameters based on its analysis of the user query."""
    
    inputs = {
        "service_url": {
            "type": "string",
            "description": "PDOK WFS service URL (from service discovery)"
        },
        "layer_name": {
            "type": "string", 
            "description": "Layer name to query (e.g. 'bag:pand', 'brk:perceel')"
        },
        "bbox": {
            "type": "string",
            "description": "Bounding box as 'minx,miny,maxx,maxy' (optional)",
            "nullable": True
        },
        "cql_filter": {
            "type": "string",
            "description": "CQL filter expression (optional)",
            "nullable": True
        },
        "max_features": {
            "type": "integer",
            "description": "Maximum features to return (default 100)",
            "nullable": True
        },
        "center_lat": {
            "type": "number",
            "description": "Center latitude for bbox calculation (optional)",
            "nullable": True
        },
        "center_lon": {
            "type": "number", 
            "description": "Center longitude for bbox calculation (optional)",
            "nullable": True
        },
        "radius_km": {
            "type": "number",
            "description": "Radius in km for bbox calculation (optional)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # Initialize coordinate transformers if available
        try:
            import pyproj
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            print("✅ PDOK Data Request Tool initialized with coordinate transformers")
        except ImportError:
            self.transformer_to_rd = None
            self.transformer_to_wgs84 = None
            print("⚠️ PyProj not available - coordinate transformation limited")
    
    def forward(self, service_url: str, layer_name: str, bbox: Optional[str] = None, 
                cql_filter: Optional[str] = None, max_features: Optional[int] = 100,
                center_lat: Optional[float] = None, center_lon: Optional[float] = None, 
                radius_km: Optional[float] = None) -> Dict:
        """Make WFS request to PDOK service."""
        try:
            print(f"🌐 Making PDOK WFS request")
            print(f"   Service: {service_url}")
            print(f"   Layer: {layer_name}")
            
            # Determine coordinate system
            if "bag" in service_url or "brk" in service_url:
                srs = "EPSG:28992"  # RD New for Dutch data
            else:
                srs = "EPSG:4326"   # WGS84
            
            # Calculate bbox if center and radius provided
            if bbox is None and center_lat and center_lon and radius_km:
                bbox = self._calculate_bbox(center_lat, center_lon, radius_km, srs)
            
            # Build WFS parameters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'srsName': srs,
                'count': max_features or 100
            }
            
            if bbox:
                params['bbox'] = f"{bbox},{srs}"
                print(f"   Bbox: {bbox}")
            
            if cql_filter:
                params['cql_filter'] = cql_filter
                print(f"   Filter: {cql_filter}")
            
            # Make request
            print(f"🚀 Executing WFS request...")
            response = requests.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"📦 Received {len(features)} features")
            
            # Process features
            processed_features = []
            for i, feature in enumerate(features):
                try:
                    processed_feature = self._process_feature(feature, srs, center_lat, center_lon)
                    if processed_feature:
                        processed_features.append(processed_feature)
                except Exception as e:
                    print(f"❌ Error processing feature {i+1}: {e}")
                    continue
            
            return {
                "features": processed_features,
                "count": len(processed_features),
                "layer": layer_name,
                "coordinate_system": srs,
                "request_info": {
                    "service_url": service_url,
                    "bbox_used": bbox,
                    "filter_used": cql_filter
                }
            }
            
        except Exception as e:
            return {"error": f"PDOK request failed: {str(e)}"}
    
    def _calculate_bbox(self, center_lat: float, center_lon: float, radius_km: float, srs: str) -> str:
        """Calculate bounding box around center point."""
        try:
            if srs == "EPSG:28992" and self.transformer_to_rd:
                # Transform to RD New
                center_x, center_y = self.transformer_to_rd.transform(center_lon, center_lat)
                radius_m = radius_km * 1000
                
                min_x = center_x - radius_m
                min_y = center_y - radius_m
                max_x = center_x + radius_m
                max_y = center_y + radius_m
                
                return f"{min_x},{min_y},{max_x},{max_y}"
            else:
                # Use WGS84 approximation
                lat_rad = math.radians(center_lat)
                km_per_degree_lat = 111.0
                km_per_degree_lon = 111.0 * math.cos(lat_rad)
                
                lat_buffer = radius_km / km_per_degree_lat
                lon_buffer = radius_km / km_per_degree_lon
                
                min_lon = center_lon - lon_buffer
                min_lat = center_lat - lat_buffer
                max_lon = center_lon + lon_buffer
                max_lat = center_lat + lat_buffer
                
                return f"{min_lon},{min_lat},{max_lon},{max_lat}"
                
        except Exception as e:
            print(f"❌ Error calculating bbox: {e}")
            return None
    
    def _process_feature(self, feature: Dict, srs: str, center_lat: Optional[float], center_lon: Optional[float]) -> Dict:
        """Process individual feature."""
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Convert geometry to WGS84 if needed
            if srs == "EPSG:28992" and self.transformer_to_wgs84:
                geometry = self._convert_geometry_to_wgs84(geometry)
            
            # Calculate centroid
            centroid = self._calculate_centroid(geometry)
            if not centroid:
                return None
            
            lat, lon = centroid
            
            # Calculate distance if center provided
            distance_km = None
            if center_lat and center_lon:
                distance_km = self._calculate_distance(center_lat, center_lon, lat, lon)
            
            # Create feature name and description
            feature_id = properties.get('identificatie', 'Unknown')
            name = f"Feature {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
            
            # Enhanced description based on properties
            desc_parts = []
            if distance_km:
                desc_parts.append(f"Distance: {distance_km:.3f}km")
            
            if properties.get('bouwjaar'):
                desc_parts.append(f"Built: {properties['bouwjaar']}")
            
            area = properties.get('oppervlakte_min') or properties.get('oppervlakte_max') or properties.get('oppervlakte')
            if area:
                desc_parts.append(f"Area: {area}m²")
            
            description = " | ".join(desc_parts) if desc_parts else "PDOK feature"
            
            return {
                "type": "Feature",
                "name": name,
                "lat": float(lat),
                "lon": float(lon),
                "description": description,
                "geometry": geometry,
                "properties": {
                    **properties,
                    "centroid_lat": float(lat),
                    "centroid_lon": float(lon),
                    "distance_km": distance_km
                }
            }
            
        except Exception as e:
            print(f"Error processing feature: {e}")
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
    
    def _calculate_centroid(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """Calculate centroid of geometry."""
        try:
            if geometry['type'] == 'Point':
                return geometry['coordinates'][1], geometry['coordinates'][0]  # lat, lon
            
            elif geometry['type'] == 'Polygon':
                coords = geometry['coordinates'][0]
                if coords:
                    avg_x = sum(c[0] for c in coords) / len(coords)
                    avg_y = sum(c[1] for c in coords) / len(coords)
                    return avg_y, avg_x  # lat, lon
            
            return None
        except Exception:
            return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using Haversine formula."""
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


# Additional utility tools for the AI
class AnalyzeCurrentMapFeatures(Tool):
    """Tool for AI to analyze current map features."""
    
    name = "analyze_current_map_features"
    description = "Analyze features currently displayed on the map and provide statistics."
    
    inputs = {}
    output_type = "object"
    is_initialized = True
    
    def forward(self) -> Dict:
        # This would be implemented to work with the current map state
        return {
            "message": "Map analysis tool - would analyze current features",
            "feature_count": 0
        }


class AnswerMapQuestion(Tool):
    """Tool for AI to answer general map/GIS questions."""
    
    name = "answer_map_question"
    description = "Answer general questions about maps, geography, GIS, and spatial analysis."
    
    inputs = {
        "question": {
            "type": "string",
            "description": "The map-related question to answer"
        }
    }
    output_type = "string"
    is_initialized = True
    
    def forward(self, question: str) -> str:
        """Answer map-related questions."""
        question_lower = question.lower()
        
        if any(term in question_lower for term in ['what is pdok', 'pdok']):
            return """PDOK (Publieke Dienstverlening Op de Kaart) is the Dutch national spatial data infrastructure. It provides free access to geographic datasets from Dutch government organizations, including building data (BAG), topographic maps, aerial imagery, and administrative boundaries."""
        
        elif any(term in question_lower for term in ['what is bag', 'buildings and addresses']):
            return """BAG (Basisregistratie Adressen en Gebouwen) is the Dutch Buildings and Addresses Database. It contains authoritative information about all buildings, addresses, and premises in the Netherlands."""
        
        else:
            return f"I can help with various map and GIS topics. Could you be more specific about what aspect of mapping or geography you'd like to know about?"