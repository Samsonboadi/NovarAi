import math
import requests
import json
from datetime import datetime
from smolagents import Tool
from typing import Dict, List, Optional, Tuple

class PDOKIntelligentAgentTool(Tool):
    name = "pdok_intelligent_agent"
    description = "Intelligent PDOK agent with service discovery and direct API filtering for buildings, verblijfsobject, parcels"
    inputs = {
        "user_request": {"type": "string", "description": "User's request (e.g., 'show buildings near Leonard Springerlaan 37, Groningen with area > 300m²')"},
        "max_features": {"type": "integer", "description": "Maximum features to return", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # WORKING PDOK endpoints (updated based on actual availability)
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "layers": {
                    "bag:pand": "Buildings (panden)",
                    "bag:verblijfsobject": "Residential objects (verblijfsobjecten)", 
                    "bag:nummeraanduiding": "Address numbers"
                }
            }
        }
        
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            print("✅ PDOK Intelligent Agent initialized")
        except ImportError:
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, user_request, max_features=50):
        try:
            print(f"🤖 Processing request: {user_request}")
            
            # Analyze request
            analysis = self._analyze_request(user_request)
            print(f"🔍 Analysis: {analysis}")
            
            # Get location coordinates
            if analysis.get('location'):
                from tools.pdok_location import find_location_coordinates
                loc_data = find_location_coordinates(analysis['location'])
                if loc_data.get('error'):
                    return {
                        "text_description": f"❌ Could not find location: {analysis['location']}",
                        "geojson_data": [],
                        "error": loc_data['error']
                    }
                
                center_coords = (loc_data['lat'], loc_data['lon'])
                print(f"📍 Location: {center_coords}")
            else:
                center_coords = None
            
            # Build and execute PDOK request
            result = self._make_pdok_request(analysis, center_coords, max_features)
            
            if result.get('error'):
                return {
                    "text_description": f"❌ PDOK request failed: {result['error']}",
                    "geojson_data": [],
                    "error": result['error']
                }
            
            features = result.get('features', [])
            print(f"📦 Raw features from PDOK: {len(features)}")
            
            # Process features
            processed = self._process_features(features, center_coords, analysis)
            
            # Create response
            text_desc = self._create_description(analysis, processed, analysis.get('location', 'the area'))
            
            return {
                "text_description": text_desc,
                "geojson_data": processed
            }
            
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _analyze_request(self, request):
        request_lower = request.lower()
        
        analysis = {
            'data_type': 'buildings',
            'service': 'bag',
            'layer': 'bag:pand',
            'location': None,
            'filters': {}
        }
        
        # Detect data type
        if any(term in request_lower for term in ['verblijfsobject', 'residential']):
            analysis.update({
                'data_type': 'verblijfsobject',
                'layer': 'bag:verblijfsobject'
            })
        
        # Extract location
        location_patterns = ['near ', 'in ', 'around ', 'at ']
        for pattern in location_patterns:
            if pattern in request_lower:
                start = request_lower.find(pattern) + len(pattern)
                # Find end of location
                end = len(request_lower)
                for end_word in [' with', ' area', ' built', ' larger', ' smaller']:
                    if end_word in request_lower[start:]:
                        end = start + request_lower[start:].find(end_word)
                        break
                
                location = request[start:end].strip()
                analysis['location'] = location
                break
        
        # Extract area filter
        if 'area' in request_lower and ('>' in request or 'larger' in request_lower):
            import re
            area_match = re.search(r'(\d+)\s*m²?', request_lower)
            if area_match:
                analysis['filters']['min_area'] = int(area_match.group(1))
        
        return analysis
    
    def _make_pdok_request(self, analysis, center_coords, max_features):
        try:
            service = self.services['bag']
            service_url = service['url']
            layer_name = analysis['layer']
            
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'count': min(max_features * 3, 1000),  # Get extra for filtering
                'srsName': 'EPSG:28992'
            }
            
            # Add spatial filter if location provided
            if center_coords:
                lat, lon = center_coords
                if self.transformer_to_rd:
                    center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                    radius_m = 2000  # 2km radius
                    bbox = [
                        center_x - radius_m, center_y - radius_m,
                        center_x + radius_m, center_y + radius_m
                    ]
                    params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
                    print(f"🗺️ Added bbox filter: {params['bbox']}")
            
            # Add CQL filter for area if specified
            if analysis['filters'].get('min_area'):
                min_area = analysis['filters']['min_area']
                if analysis['data_type'] == 'buildings':
                    params['cql_filter'] = f"oppervlakte_min >= {min_area}"
                    print(f"🔍 Added area filter: {params['cql_filter']}")
            
            print(f"🚀 Making PDOK request: {service_url}")
            print(f"📋 Parameters: {params}")
            
            response = requests.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"✅ PDOK returned {len(features)} features")
            
            return {"features": features}
            
        except Exception as e:
            return {"error": f"PDOK request failed: {str(e)}"}
    
    def _process_features(self, features, center_coords, analysis):
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
                
                # Calculate distance if center provided
                distance_km = None
                if center_coords:
                    distance_km = self._calculate_distance(center_coords[0], center_coords[1], lat, lon)
                
                # Additional area filtering for precision
                if analysis['filters'].get('min_area'):
                    area = props.get('oppervlakte_min') or props.get('oppervlakte_max', 0)
                    if area < analysis['filters']['min_area']:
                        continue
                
                # Create feature
                feature_id = props.get('identificatie', f'Feature_{i+1}')
                name = f"{analysis['data_type'].title()} {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
                
                desc_parts = []
                if distance_km:
                    desc_parts.append(f"Distance: {distance_km:.3f}km")
                
                if analysis['data_type'] == 'buildings':
                    if props.get('bouwjaar'):
                        desc_parts.append(f"Built: {props['bouwjaar']}")
                    area = props.get('oppervlakte_min') or props.get('oppervlakte_max')
                    if area:
                        desc_parts.append(f"Area: {area}m²")
                elif analysis['data_type'] == 'verblijfsobject':
                    if props.get('gebruiksdoel'):
                        desc_parts.append(f"Use: {props['gebruiksdoel']}")
                    if props.get('oppervlakte'):
                        desc_parts.append(f"Area: {props['oppervlakte']}m²")
                
                description = " | ".join(desc_parts) if desc_parts else f"{analysis['data_type'].title()} info"
                
                # Convert geometry to WGS84
                wgs84_geom = self._convert_geometry_to_wgs84(geometry)
                
                processed_feature = {
                    "name": name,
                    "lat": float(lat),
                    "lon": float(lon),
                    "description": description,
                    "geometry": wgs84_geom,
                    "properties": {
                        **props,
                        "centroid_lat": float(lat),
                        "centroid_lon": float(lon),
                        "distance_km": distance_km,
                        "data_type": analysis['data_type']
                    }
                }
                
                processed.append(processed_feature)
                
            except Exception as e:
                print(f"❌ Error processing feature {i+1}: {e}")
                continue
        
        # Sort by distance if available
        if center_coords:
            processed.sort(key=lambda x: x['properties'].get('distance_km', 999))
        
        return processed
    
    def _get_centroid_wgs84(self, geometry):
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
        except:
            return None
    
    def _convert_geometry_to_wgs84(self, geometry):
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
        except:
            return geometry
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        try:
            R = 6371
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                math.cos(lat1_rad) * math.cos(lat2_rad) * 
                math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        except:
            return 999.0
    
    def _create_description(self, analysis, features, location):
        if not features:
            return f"❌ No {analysis['data_type']} found in {location} matching your criteria."
        
        text_parts = []
        text_parts.append(f"## {analysis['data_type'].title()} in {location}")
        text_parts.append(f"\nI found **{len(features)} {analysis['data_type']}** in {location} using PDOK BAG service.")
        
        if analysis['filters'].get('min_area'):
            text_parts.append(f"**Filter applied**: area ≥ {analysis['filters']['min_area']}m²")
        
        # Add sample features
        text_parts.append(f"\n**Sample {analysis['data_type']}**:")
        for feature in features[:5]:
            text_parts.append(f"* **{feature['name']}** - {feature['description']}")
        
        if len(features) > 5:
            text_parts.append(f"... and {len(features) - 5} more")
        
        text_parts.append(f"\n**FIXED APPROACH**: Uses direct API filtering with PDOK BAG service for targeted results.")
        
        return "\n".join(text_parts)


class EnhancedPDOKServiceDiscoveryTool(Tool):
    name = "discover_pdok_services_enhanced"
    description = "Enhanced PDOK service discovery with real-time availability checking"
    inputs = {
        "service_type": {"type": "string", "description": "Service type: 'all', 'bag'", "nullable": True},
        "check_availability": {"type": "boolean", "description": "Check if services are available", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # WORKING services only (based on actual availability)
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "layers": {
                    "bag:pand": "Buildings (panden)",
                    "bag:verblijfsobject": "Residential objects (verblijfsobjecten)", 
                    "bag:nummeraanduiding": "Address numbers",
                    "bag:openbare_ruimte": "Public spaces",
                    "bag:woonplaats": "Residential places"
                },
                "description": "Dutch Buildings and Addresses Database - WORKING"
            }
        }
    
    def forward(self, service_type="all", check_availability=True):
        try:
            services = self.services.copy()
            
            if service_type != "all" and service_type in services:
                services = {service_type: services[service_type]}
            
            if check_availability:
                for service_key, service_info in services.items():
                    availability = self._check_availability(service_info['url'])
                    service_info['availability'] = availability
            
            return {
                "services": services,
                "total_services": len(services),
                "availability_checked": check_availability,
                "recommendations": {
                    "buildings": "Use 'bag' service with 'bag:pand' layer",
                    "addresses": "Use 'bag' service with 'bag:nummeraanduiding' layer",
                    "residential_objects": "Use 'bag' service with 'bag:verblijfsobject' layer"
                },
                "working_services": ["BAG - Buildings and Addresses"],
                "note": "Only BAG service is currently working. Other PDOK services return 404 errors."
            }
            
        except Exception as e:
            return {"error": f"Service discovery error: {str(e)}"}
    
    def _check_availability(self, service_url):
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            response = requests.get(service_url, params=params, timeout=10)
            response.raise_for_status()
            
            if 'xml' in response.headers.get('content-type', '').lower():
                return {"available": True}
            else:
                return {"available": False, "error": "Invalid response format"}
                
        except Exception as e:
            return {"available": False, "error": str(e)}