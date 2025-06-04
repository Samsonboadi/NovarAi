# tools/enhanced_ai_intelligent_tools.py

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple

class EnhancedPDOKServiceDiscoveryTool(Tool):
    """
    Enhanced service discovery tool that gets detailed attribute information.
    The AI uses this to understand exactly what attributes are available for filtering.
    """
    
    name = "discover_pdok_services"
    description = """Discover available PDOK WFS services, layers, and their detailed attributes.

This tool helps the AI understand what PDOK services, layers, and attributes are available.
The AI should use this to learn about available endpoints AND their filterable attributes.

Returns detailed information about:
- Available WFS services (BAG, BGT, BRK, CBS)
- Layers within each service with descriptions
- Available attributes for each layer (for CQL filtering)
- Data types and constraints for attributes
- Service availability status

The AI can then use this information to select appropriate services and construct proper CQL filters with correct attribute names."""
    
    inputs = {
        "service_name": {
            "type": "string", 
            "description": "Specific service to check (bag, bgt, brk, cbs) or 'all' for all services",
            "nullable": True
        },
        "get_attributes": {
            "type": "boolean",
            "description": "Whether to get detailed attribute information for layers (default: True)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # Known PDOK services for the AI to discover
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "description": "Dutch Buildings and Addresses Database",
                "typical_use": "Buildings (panden), addresses (nummeraanduiding), residential objects (verblijfsobject)"
            },
            "bgt": {
                "name": "BGT - Large Scale Topography", 
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                "description": "Detailed topographic features",
                "typical_use": "Building surfaces, roads, water features, land use"
            },
            "brk": {
                "name": "BRK - Cadastral Registry",
                "url": "https://service.pdok.nl/lv/brk/wfs/v2_0",
                "description": "Land parcels and ownership information",
                "typical_use": "Land parcels (perceel), ownership rights (zakelijkrecht)"
            },
            "cbs": {
                "name": "CBS - Statistics Netherlands",
                "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
                "description": "Administrative boundaries and statistics",
                "typical_use": "Municipalities (gemeenten), districts (wijken), neighborhoods (buurten)"
            }
        }
    
    def forward(self, service_name: Optional[str] = "all", get_attributes: Optional[bool] = True) -> Dict:
        """Enhanced discovery with detailed attribute information."""
        try:
            print(f"🔍 Enhanced PDOK discovery: {service_name} (attributes: {get_attributes})")
            
            if service_name == "all" or service_name is None:
                discovered_services = {}
                
                for key, config in self.services.items():
                    print(f"📡 Checking {key} with detailed analysis...")
                    capabilities = self._get_enhanced_capabilities(config["url"], get_attributes)
                    
                    discovered_services[key] = {
                        **config,
                        "capabilities": capabilities,
                        "available": not capabilities.get('error'),
                        "layers": capabilities.get('layers', [])
                    }
                
                return {
                    "services": discovered_services,
                    "summary": f"Enhanced discovery of {len(discovered_services)} PDOK services",
                    "ai_guidance": {
                        "for_buildings": "Use 'bag' service with 'bag:pand' layer",
                        "for_addresses": "Use 'bag' service with 'bag:nummeraanduiding'",
                        "for_parcels": "Use 'brk' service with 'brk:perceel'",
                        "for_boundaries": "Use 'cbs' service for administrative boundaries",
                        "attribute_usage": "Check 'attributes' field for each layer to see available filter fields"
                    }
                }
            
            elif service_name in self.services:
                config = self.services[service_name]
                capabilities = self._get_enhanced_capabilities(config["url"], get_attributes)
                
                return {
                    "service": {
                        **config,
                        "capabilities": capabilities,
                        "available": not capabilities.get('error'),
                        "layers": capabilities.get('layers', [])
                    }
                }
            
            else:
                return {"error": f"Unknown service: {service_name}. Available: {list(self.services.keys())}"}
                
        except Exception as e:
            return {"error": f"Enhanced service discovery error: {str(e)}"}
    
    def _get_enhanced_capabilities(self, service_url: str, get_attributes: bool = True) -> Dict:
        """Get enhanced WFS capabilities with attribute information."""
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
                        
                        # Get detailed attribute information if requested
                        if get_attributes:
                            attributes = self._get_layer_attributes(service_url, name_elem.text)
                            layer_info["attributes"] = attributes
                            layer_info["filter_guidance"] = self._generate_filter_guidance(attributes, name_elem.text)
                        
                        layers.append(layer_info)
            
            return {
                "layers": layers,
                "layer_count": len(layers),
                "service_operational": True,
                "attributes_included": get_attributes
            }
            
        except Exception as e:
            return {"error": f"Could not get enhanced capabilities: {str(e)}"}
    
    def _get_layer_attributes(self, service_url: str, layer_name: str) -> Dict:
        """Get detailed attribute information for a specific layer."""
        try:
            print(f"🔬 Getting attributes for layer: {layer_name}")
            
            # Make DescribeFeatureType request to get attribute details
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'DescribeFeatureType',
                'typeName': layer_name
            }
            
            response = requests.get(service_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse the schema to extract attribute information
            root = ET.fromstring(response.content)
            
            attributes = {}
            
            # Look for complexType and sequence elements
            for complex_type in root.iter():
                if complex_type.tag.endswith('complexType'):
                    for sequence in complex_type.iter():
                        if sequence.tag.endswith('sequence'):
                            for element in sequence.iter():
                                if element.tag.endswith('element'):
                                    attr_name = element.get('name')
                                    attr_type = element.get('type', 'unknown')
                                    
                                    if attr_name and attr_name not in ['geometry', 'geom']:
                                        attributes[attr_name] = {
                                            "type": attr_type,
                                            "filterable": True
                                        }
                                        
                                        # Add guidance for common attribute patterns
                                        if any(word in attr_name.lower() for word in ['oppervlakte', 'area', 'grootte']):
                                            attributes[attr_name]["usage"] = "Use for area filtering (numeric)"
                                            attributes[attr_name]["example"] = f"{attr_name} >= 300"
                                        
                                        elif any(word in attr_name.lower() for word in ['jaar', 'year', 'bouw']):
                                            attributes[attr_name]["usage"] = "Use for year filtering (numeric)"
                                            attributes[attr_name]["example"] = f"{attr_name} <= 1950"
                                        
                                        elif any(word in attr_name.lower() for word in ['status', 'type', 'functie']):
                                            attributes[attr_name]["usage"] = "Use for categorical filtering (text)"
                                            attributes[attr_name]["example"] = f"{attr_name} = 'some_value'"
            
            # If no attributes found via schema, try a sample feature request
            if not attributes:
                print(f"🔍 No attributes from schema, trying sample feature...")
                attributes = self._get_attributes_from_sample(service_url, layer_name)
            
            return {
                "count": len(attributes),
                "details": attributes,
                "discovery_method": "DescribeFeatureType" if attributes else "sample_feature"
            }
            
        except Exception as e:
            print(f"⚠️ Could not get attributes for {layer_name}: {e}")
            return {"error": f"Could not get attributes: {str(e)}"}
    
    def _get_attributes_from_sample(self, service_url: str, layer_name: str) -> Dict:
        """Get attributes by requesting a sample feature."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'count': 1  # Just get one feature to see attributes
            }
            
            response = requests.get(service_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            attributes = {}
            
            if features:
                properties = features[0].get('properties', {})
                for attr_name, attr_value in properties.items():
                    attr_type = type(attr_value).__name__
                    
                    attributes[attr_name] = {
                        "type": attr_type,
                        "filterable": True,
                        "sample_value": str(attr_value)[:50]  # First 50 chars
                    }
                    
                    # Add usage guidance
                    if any(word in attr_name.lower() for word in ['oppervlakte', 'area', 'grootte']):
                        attributes[attr_name]["usage"] = "Use for area filtering (numeric)"
                        attributes[attr_name]["example"] = f"{attr_name} >= 300"
                    
                    elif any(word in attr_name.lower() for word in ['jaar', 'year', 'bouw']):
                        attributes[attr_name]["usage"] = "Use for year filtering (numeric)"
                        attributes[attr_name]["example"] = f"{attr_name} <= 1950"
            
            return attributes
            
        except Exception as e:
            print(f"⚠️ Sample feature request failed: {e}")
            return {}
    
    def _generate_filter_guidance(self, attributes: Dict, layer_name: str) -> Dict:
        """Generate AI guidance for using attributes in CQL filters."""
        guidance = {
            "available_filters": [],
            "examples": [],
            "recommendations": []
        }
        
        if attributes.get('details'):
            for attr_name, attr_info in attributes['details'].items():
                if attr_info.get('filterable'):
                    guidance["available_filters"].append({
                        "attribute": attr_name,
                        "type": attr_info.get('type', 'unknown'),
                        "usage": attr_info.get('usage', 'General filtering'),
                        "example": attr_info.get('example', f"{attr_name} = 'value'")
                    })
        
        # Add specific recommendations based on layer type
        if 'pand' in layer_name.lower():
            guidance["recommendations"].extend([
                "For building area filtering, look for attributes containing 'oppervlakte'",
                "For building age filtering, look for attributes containing 'bouwjaar'",
                "For building status filtering, look for 'status' attributes"
            ])
        
        elif 'verblijfsobject' in layer_name.lower():
            guidance["recommendations"].extend([
                "For residential area filtering, look for 'oppervlakte' attributes",
                "For usage type filtering, look for 'gebruiksdoel' attributes"
            ])
        
        return guidance


# Keep the existing LocationSearchTool and PDOKDataRequestTool from the previous version
# but update their imports and usage

class LocationSearchTool(Tool):
    """Location search tool for the AI to find coordinates."""
    
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
    """PDOK data request tool for the AI to make WFS requests."""
    
    name = "request_pdok_data"
    description = """Make WFS requests to PDOK services.

The AI should use this tool after:
1. Using discover_pdok_services to understand available endpoints and attributes
2. Using search_location_coordinates to get coordinates if needed
3. Determining the appropriate service URL, layer, and filters based on discovery

The AI constructs the parameters based on its analysis and discovery results."""
    
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
            "description": "CQL filter expression using correct attribute names from discovery (optional)",
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
            print("✅ Enhanced PDOK Data Request Tool initialized with coordinate transformers")
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
            print(f"🌐 Making enhanced PDOK WFS request")
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
                print(f"   CQL Filter: {cql_filter}")
            
            # Make request
            print(f"🚀 Executing enhanced WFS request...")
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
                        
                        # Debug first few features
                        if i < 3:
                            props = processed_feature.get('properties', {})
                            print(f"   Feature {i+1}: {processed_feature.get('name', 'Unknown')}")
                            # Show some key properties
                            for key, value in list(props.items())[:3]:
                                print(f"     {key}: {value}")
                            
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
                    "filter_used": cql_filter,
                    "original_count": len(features),
                    "processed_count": len(processed_features)
                }
            }
            
        except Exception as e:
            return {"error": f"Enhanced PDOK request failed: {str(e)}"}
    
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
            
            # Create enhanced feature name and description
            feature_id = properties.get('identificatie', 'Unknown')
            name = f"Feature {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
            
            # Enhanced description based on properties
            desc_parts = []
            if distance_km:
                desc_parts.append(f"Distance: {distance_km:.3f}km")
            
            # Check for common building attributes
            if properties.get('bouwjaar'):
                desc_parts.append(f"Built: {properties['bouwjaar']}")
            
            # Check for various area attributes (the AI will learn these from discovery)
            area = None
            for area_field in ['oppervlakte_min', 'oppervlakte_max', 'oppervlakte', 'area']:
                if properties.get(area_field):
                    area = properties[area_field]
                    break
            
            if area:
                desc_parts.append(f"Area: {area}m²")
            
            # Add status if available
            if properties.get('status'):
                desc_parts.append(f"Status: {properties['status']}")
            
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
            print(f"Error processing enhanced feature: {e}")
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