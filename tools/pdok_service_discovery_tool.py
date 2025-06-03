# tools/flexible_pdok_tools.py - Modular PDOK Tools for Better Flexibility

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union

class PDOKServiceDiscoveryTool(Tool):
    """
    Discover available PDOK WFS services and their capabilities.
    This tool helps the agent understand what layers are available.
    """
    
    name = "discover_pdok_services"
    description = "Discover available PDOK WFS services, layers, and their capabilities to help select the right endpoint"
    inputs = {
        "service_type": {"type": "string", "description": "Type of service to discover: 'bag' (buildings), 'bgt' (topography), 'brk' (cadastral), 'all'", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # Known PDOK WFS services
        self.services = {
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "layers": ["bag:pand", "bag:verblijfsobject", "bag:nummeraanduiding"],
                "description": "Dutch Buildings and Addresses Database"
            },
            "bgt": {
                "name": "BGT - Large Scale Topography", 
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                "layers": ["bgt:gebouw_vlak", "bgt:wegdeel_vlak", "bgt:waterdeel_vlak"],
                "description": "Detailed topographic features"
            },
            "brk": {
                "name": "C",
                "url": "https://service.pdok.nl/lv/brk/wfs/v2_0", 
                "layers": ["brk:perceel", "brk:zakelijkrecht"],
                "description": "Land parcels and ownership"
            },
            "cbs": {
                "name": "CBS - Statistics Netherlands",
                "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
                "layers": ["cbs:wijken", "cbs:buurten", "cbs:gemeenten"],
                "description": "Administrative boundaries and statistics"
            }
        }
    
    def forward(self, service_type="all"):
        """Discover PDOK services and their capabilities."""
        try:
            print(f"🔍 Discovering PDOK services for: {service_type}")
            
            if service_type == "all":
                return {
                    "services": self.services,
                    "summary": f"Found {len(self.services)} PDOK WFS services",
                    "recommendations": {
                        "buildings": "Use 'bag' service with 'bag:pand' layer",
                        "addresses": "Use 'bag' service with 'bag:nummeraanduiding' layer", 
                        "parcels": "Use 'brk' service with 'brk:perceel' layer",
                        "topography": "Use 'bgt' service with appropriate layers"
                    }
                }
            
            elif service_type in self.services:
                service = self.services[service_type]
                
                # Try to get GetCapabilities for detailed info
                capabilities = self._get_capabilities(service["url"])
                
                return {
                    "service": service,
                    "capabilities": capabilities,
                    "recommendation": f"Use {service['url']} for {service['description']}"
                }
            
            else:
                return {
                    "error": f"Unknown service type: {service_type}",
                    "available_services": list(self.services.keys())
                }
                
        except Exception as e:
            return {"error": f"Service discovery error: {str(e)}"}
    
    def _get_capabilities(self, service_url):
        """Get WFS capabilities for a service."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            response = requests.get(service_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML to extract layer info
            root = ET.fromstring(response.content)
            
            layers = []
            for feature_type in root.iter():
                if feature_type.tag.endswith('FeatureType'):
                    name_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Name')
                    title_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Title')
                    
                    if name_elem is not None:
                        layer_info = {
                            "name": name_elem.text,
                            "title": title_elem.text if title_elem is not None else name_elem.text
                        }
                        layers.append(layer_info)
            
            return {
                "layers_found": len(layers),
                "layers": layers[:10],  # Limit to first 10
                "service_available": True
            }
            
        except Exception as e:
            return {"error": f"Could not get capabilities: {str(e)}"}

class PDOKDataRequestTool(Tool):
    """
    Make flexible WFS requests to PDOK services based on discovered capabilities.
    This tool can work with any PDOK WFS service and layer.
    """
    
    name = "request_pdok_data"
    description = "Make WFS requests to PDOK services with flexible parameters for any layer"
    inputs = {
        "service_url": {"type": "string", "description": "PDOK WFS service URL"},
        "layer_name": {"type": "string", "description": "Layer name (e.g., 'bag:pand', 'brk:perceel')"},
        "bbox": {"type": "string", "description": "Bounding box as 'minx,miny,maxx,maxy' or 'auto' for Netherlands", "nullable": True},
        "cql_filter": {"type": "string", "description": "CQL filter expression", "nullable": True},
        "max_features": {"type": "integer", "description": "Maximum features to return", "nullable": True},
        "center_lat": {"type": "number", "description": "Center latitude for bbox calculation", "nullable": True},
        "center_lon": {"type": "number", "description": "Center longitude for bbox calculation", "nullable": True},
        "radius_km": {"type": "number", "description": "Radius in km for bbox calculation", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):  # <-- THIS IS THE __init__ METHOD TO UPDATE
            super().__init__()
            try:
                import pyproj
                
                # FIXED: Ensure proper coordinate order handling
                self.transformer_to_rd = pyproj.Transformer.from_crs(
                    "EPSG:4326", "EPSG:28992", always_xy=True
                )
                self.transformer_to_wgs84 = pyproj.Transformer.from_crs(
                    "EPSG:28992", "EPSG:4326", always_xy=True
                )
                
                # Test the transformation with a known point (Utrecht)
                test_lon, test_lat = 5.095204, 52.088692  # Utrecht WGS84
                rd_x, rd_y = self.transformer_to_rd.transform(test_lon, test_lat)
                print(f"✅ Coordinate transformers initialized for PDOK data requests")
                print(f"   Test: Utrecht WGS84 ({test_lon}, {test_lat}) → RD New ({rd_x:.2f}, {rd_y:.2f})")
                
                # Utrecht should be around (136000, 455000) in RD New
                if 130000 < rd_x < 145000 and 450000 < rd_y < 465000:
                    print(f"✅ Coordinate transformation validation: PASSED")
                else:
                    print(f"⚠️  Coordinate transformation validation: QUESTIONABLE")
                    print(f"   Expected: X=130000-145000, Y=450000-465000")
                    print(f"   Got: X={rd_x:.2f}, Y={rd_y:.2f}")
                    
            except ImportError:
                print("❌ PyProj not available for PDOK data requests - using WGS84 coordinates only")
                self.transformer_to_rd = None
                self.transformer_to_wgs84 = None
    
    def forward(self, service_url, layer_name, bbox="auto", cql_filter=None, max_features=100, 
                center_lat=None, center_lon=None, radius_km=None):
        """Make a flexible WFS request to PDOK."""
        try:
            print(f"🌐 Making PDOK WFS request")
            print(f"   Service: {service_url}")
            print(f"   Layer: {layer_name}")
            print(f"   Max features: {max_features}")
            
            # Determine coordinate system based on service
            if "bag" in service_url or "brk" in service_url:
                srs = "EPSG:28992"  # RD New for Dutch national data
            else:
                srs = "EPSG:4326"   # WGS84 for international compatibility
            
            # Calculate bounding box
            if bbox == "auto":
                if center_lat and center_lon and radius_km:
                    bbox_coords = self._calculate_bbox(center_lat, center_lon, radius_km, srs)
                else:
                    # Default to Netherlands bounds
                    if srs == "EPSG:28992":
                        bbox_coords = "10000,300000,280000,620000"  # Netherlands in RD New
                    else:
                        bbox_coords = "3.2,50.7,7.3,53.6"  # Netherlands in WGS84
            else:
                bbox_coords = bbox
            
            # Build WFS request parameters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'srsName': srs,
                'count': max_features
            }
            
            if bbox_coords:
                params['bbox'] = f"{bbox_coords},{srs}"
                print(f"   Bbox: {bbox_coords}")
            
            if cql_filter:
                params['cql_filter'] = cql_filter
                print(f"   Filter: {cql_filter}")
            
            # Make the request
            print(f"🚀 Executing WFS request...")
            response = requests.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"📦 Received {len(features)} features from PDOK")
            
            if not features:
                return {
                    "features": [],
                    "count": 0,
                    "message": f"No features found for {layer_name}",
                    "request_params": params
                }
            
            # Basic feature processing
            processed_features = []
            for i, feature in enumerate(features):
                try:
                    processed_feature = self._process_feature(feature, srs)
                    if processed_feature:
                        processed_features.append(processed_feature)
                        
                        if i < 3:  # Debug first few features
                            props = processed_feature.get('properties', {})
                            print(f"   Feature {i+1}: {props.get('identificatie', 'No ID')}")
                            
                except Exception as e:
                    print(f"❌ Error processing feature {i+1}: {e}")
                    continue
            
            print(f"✅ Successfully processed {len(processed_features)} features")
            
            return {
                "features": processed_features,
                "count": len(processed_features),
                "layer": layer_name,
                "coordinate_system": srs,
                "request_params": params,
                "bbox_used": bbox_coords
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"WFS request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Data request error: {str(e)}"}
    
    def _calculate_bbox(self, center_lat, center_lon, radius_km, srs):
        """Calculate bounding box around center point - FIXED VERSION."""
        try:
            print(f"🧮 Calculating bbox: center=({center_lat:.6f}, {center_lon:.6f}), radius={radius_km}km, srs={srs}")
            
            if srs == "EPSG:28992" and self.transformer_to_rd:
                center_x, center_y = self.transformer_to_rd.transform(center_lon, center_lat)
                print(f"🔄 RD New conversion: ({center_lon:.6f}, {center_lat:.6f}) → ({center_x:.2f}, {center_y:.2f})")
                
                # FIXED: Use much smaller buffer - PDOK seems to ignore large bboxes
                radius_m = radius_km * 800  # Use only 80% of requested radius for bbox
                
                min_x = center_x - radius_m
                min_y = center_y - radius_m
                max_x = center_x + radius_m
                max_y = center_y + radius_m
                
                bbox = f"{min_x},{min_y},{max_x},{max_y}"
                print(f"📦 RD New bbox (tighter): {bbox}")
                
                # ADDED: Debug bbox corners
                if self.transformer_to_wgs84:
                    corners = [(min_x, min_y), (max_x, max_y)]
                    print(f"🗺️  Bbox covers:")
                    for i, (x, y) in enumerate(corners):
                        lon, lat = self.transformer_to_wgs84.transform(x, y)
                        corner_name = ["SW", "NE"][i]
                        print(f"   {corner_name}: {lat:.6f}°N, {lon:.6f}°E")
                
                return bbox
                
            else:
                # WGS84 with tighter bounds
                lat_rad = math.radians(center_lat)
                km_per_degree_lat = 111.0
                km_per_degree_lon = 111.0 * math.cos(lat_rad)
                
                # Use smaller buffer for WGS84 too
                lat_buffer = (radius_km * 0.8) / km_per_degree_lat
                lon_buffer = (radius_km * 0.8) / km_per_degree_lon
                
                min_lon = center_lon - lon_buffer
                min_lat = center_lat - lat_buffer
                max_lon = center_lon + lon_buffer
                max_lat = center_lat + lat_buffer
                
                bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
                print(f"📦 WGS84 bbox (tighter): {bbox}")
                return bbox
                
        except Exception as e:
            print(f"❌ Error calculating bbox: {e}")
            return None
    
    def _process_feature(self, feature, srs):
        """Process individual feature and convert coordinates if needed."""
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Convert geometry to WGS84 if it's in RD New
            if srs == "EPSG:28992" and self.transformer_to_wgs84:
                geometry = self._convert_geometry_to_wgs84(geometry)
            
            # Calculate centroid for lat/lon fields
            centroid = self._calculate_centroid(geometry)
            
            return {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry,
                "lat": centroid[1] if centroid else 0,
                "lon": centroid[0] if centroid else 0
            }
            
        except Exception as e:
            print(f"Error processing feature: {e}")
            return None
    
    def _convert_geometry_to_wgs84(self, geometry):
        """Convert geometry from RD New to WGS84."""
        try:
            if not self.transformer_to_wgs84:
                return geometry
            
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates')
            
            if geom_type == 'Point':
                wgs84_coord = self.transformer_to_wgs84.transform(coordinates[0], coordinates[1])
                return {
                    'type': 'Point',
                    'coordinates': [wgs84_coord[0], wgs84_coord[1]]
                }
            
            elif geom_type == 'Polygon':
                wgs84_coords = []
                for ring in coordinates:
                    wgs84_ring = []
                    for coord in ring:
                        wgs84_coord = self.transformer_to_wgs84.transform(coord[0], coord[1])
                        wgs84_ring.append([wgs84_coord[0], wgs84_coord[1]])
                    wgs84_coords.append(wgs84_ring)
                
                return {
                    'type': 'Polygon',
                    'coordinates': wgs84_coords
                }
            
            return geometry
            
        except Exception as e:
            print(f"Error converting geometry: {e}")
            return geometry
    
    def _calculate_centroid(self, geometry):
        """Calculate centroid of geometry."""
        try:
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates')
            
            if geom_type == 'Point':
                return coordinates
            
            elif geom_type == 'Polygon' and coordinates:
                exterior = coordinates[0]
                if exterior:
                    avg_x = sum(coord[0] for coord in exterior) / len(exterior)
                    avg_y = sum(coord[1] for coord in exterior) / len(exterior)
                    return [avg_x, avg_y]
            
            return None
            
        except Exception:
            return None

class PDOKDataFilterTool(Tool):
    """
    Filter and process PDOK data results based on various criteria.
    This tool works with the raw data from PDOKDataRequestTool.
    FIXED: Proper handling of None values in area and year comparisons.
    """
    
    name = "filter_pdok_data"
    description = "Filter and process PDOK data results by distance, age, area, or other criteria"
    inputs = {
        "features": {"type": "object", "description": "Raw features from PDOK request"},
        "center_lat": {"type": "number", "description": "Center latitude for distance calculation", "nullable": True},
        "center_lon": {"type": "number", "description": "Center longitude for distance calculation", "nullable": True},
        "max_distance_km": {"type": "number", "description": "Maximum distance from center in km", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "min_area_m2": {"type": "number", "description": "Minimum area in square meters", "nullable": True},
        "max_area_m2": {"type": "number", "description": "Maximum area in square meters", "nullable": True},
        "sort_by": {"type": "string", "description": "Sort by: 'distance', 'age', 'area', 'year'", "nullable": True},
        "limit": {"type": "integer", "description": "Maximum number of results", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, features, center_lat=None, center_lon=None, max_distance_km=None,
                min_year=None, max_year=None, min_area_m2=None, max_area_m2=None,
                sort_by="distance", limit=20):
        """Filter and process PDOK features with proper None value handling."""
        try:
            print(f"🔽 Filtering PDOK data")
            
            # Handle different input formats correctly
            if isinstance(features, dict):
                if 'features' in features:
                    feature_list = features['features']
                    print(f"   Input features: {len(feature_list)} from dict")
                else:
                    print(f"   Input features: Invalid dict format")
                    return {"error": "Invalid features format - expected list or dict with 'features' key"}
            elif isinstance(features, list):
                feature_list = features
                print(f"   Input features: {len(feature_list)} from list")
            else:
                print(f"   Input features: Invalid type {type(features)}")
                return {"error": "Features must be a list or dict"}
            
            if not feature_list:
                return {
                    "filtered_features": [],
                    "count": 0,
                    "message": "No features to filter"
                }
            
            filtered_features = []
            
            for i, feature in enumerate(feature_list):
                try:
                    # Extract feature data
                    if isinstance(feature, dict):
                        properties = feature.get('properties', {})
                        geometry = feature.get('geometry', {})
                        
                        # Get coordinates
                        feat_lat = feature.get('lat', 0)
                        feat_lon = feature.get('lon', 0)
                        
                        if feat_lat == 0 or feat_lon == 0:
                            # Try to calculate from geometry
                            centroid = self._calculate_centroid(geometry)
                            if centroid:
                                feat_lon, feat_lat = centroid
                        
                        # Apply filters with proper None handling
                        passes_filters = True
                        filter_reasons = []
                        
                        # Distance filter with proper calculation
                        distance_km = None
                        if center_lat and center_lon and feat_lat != 0 and feat_lon != 0:
                            distance_km = self._haversine_distance(center_lat, center_lon, feat_lat, feat_lon)
                            
                            if max_distance_km and distance_km > max_distance_km:
                                passes_filters = False
                                filter_reasons.append(f"distance {distance_km:.2f}km > {max_distance_km}km")
                        
                        # FIXED: Year filters with None handling
                        building_year = properties.get('bouwjaar')
                        if building_year is not None and isinstance(building_year, (int, float)):
                            building_year = int(building_year)
                            if min_year and building_year < min_year:
                                passes_filters = False
                                filter_reasons.append(f"year {building_year} < {min_year}")
                            
                            if max_year and building_year > max_year:
                                passes_filters = False
                                filter_reasons.append(f"year {building_year} > {max_year}")
                        else:
                            # If year filtering is requested but building has no year, exclude it
                            if min_year or max_year:
                                passes_filters = False
                                filter_reasons.append(f"no year data (required for age filter)")
                                building_year = None
                        
                        # FIXED: Area filters with None handling
                        area_m2 = None
                        # Try multiple area fields
                        for area_field in ['oppervlakte_min', 'oppervlakte_max', 'area_m2']:
                            area_value = properties.get(area_field)
                            if area_value is not None and isinstance(area_value, (int, float)) and area_value > 0:
                                area_m2 = float(area_value)
                                break
                        
                        if area_m2 is not None:
                            if min_area_m2 and area_m2 < min_area_m2:
                                passes_filters = False
                                filter_reasons.append(f"area {area_m2:.0f}m² < {min_area_m2}m²")
                            
                            if max_area_m2 and area_m2 > max_area_m2:
                                passes_filters = False
                                filter_reasons.append(f"area {area_m2:.0f}m² > {max_area_m2}m²")
                        else:
                            # If area filtering is requested but building has no area, exclude it
                            if min_area_m2 or max_area_m2:
                                passes_filters = False
                                filter_reasons.append(f"no area data (required for area filter)")
                        
                        if passes_filters:
                            # Add computed fields
                            enhanced_feature = {
                                **feature,
                                "distance_km": distance_km,
                                "building_year": building_year,
                                "area_m2": area_m2,
                                "lat": feat_lat,
                                "lon": feat_lon
                            }
                            
                            filtered_features.append(enhanced_feature)
                            
                            if i < 5:  # Debug first few
                                feature_id = properties.get('identificatie', f'Feature_{i+1}')
                                if len(feature_id) > 10:
                                    feature_id = feature_id[-6:]
                                print(f"   ✅ Feature {feature_id}: distance={distance_km:.3f if distance_km else 'N/A'}km, year={building_year}, area={area_m2:.0f if area_m2 else 'N/A'}m²")
                        
                        else:
                            if i < 5:  # Debug rejections
                                feature_id = properties.get('identificatie', f'Feature_{i+1}')
                                if len(feature_id) > 10:
                                    feature_id = feature_id[-6:]
                                print(f"   ❌ Rejected {feature_id}: {', '.join(filter_reasons)}")
                    
                except Exception as e:
                    print(f"❌ Error processing feature {i+1}: {e}")
                    continue
            
            print(f"📊 Filtered to {len(filtered_features)} features")
            
            # Sort results with proper None handling
            if sort_by == "distance" and center_lat and center_lon:
                filtered_features.sort(key=lambda x: x.get('distance_km') if x.get('distance_km') is not None else 999)
            elif sort_by == "age" or sort_by == "year":
                filtered_features.sort(key=lambda x: x.get('building_year') if x.get('building_year') is not None else 0)
            elif sort_by == "area":
                filtered_features.sort(key=lambda x: x.get('area_m2') if x.get('area_m2') is not None else 0, reverse=True)
            
            # Apply limit
            if limit and len(filtered_features) > limit:
                filtered_features = filtered_features[:limit]
                print(f"📏 Limited to {limit} results")
            
            return {
                "filtered_features": filtered_features,
                "count": len(filtered_features),
                "filters_applied": {
                    "max_distance_km": max_distance_km,
                    "min_year": min_year,
                    "max_year": max_year,
                    "min_area_m2": min_area_m2,
                    "max_area_m2": max_area_m2
                },
                "sorted_by": sort_by
            }
            
        except Exception as e:
            return {"error": f"Filtering error: {str(e)}"}
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula - FIXED."""
        try:
            # Validate inputs
            if not all(isinstance(coord, (int, float)) for coord in [lat1, lon1, lat2, lon2]):
                print(f"⚠️  Invalid coordinates for distance calculation")
                return 999.0
                
            if lat1 == 0 or lon1 == 0 or lat2 == 0 or lon2 == 0:
                print(f"⚠️  Zero coordinates detected in distance calculation")
                return 999.0
            
            import math
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                math.cos(lat1_rad) * math.cos(lat2_rad) * 
                math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            distance = R * c
            
            # Debug for first few calculations
            if hasattr(self, '_debug_count'):
                self._debug_count += 1
            else:
                self._debug_count = 1
                
            if self._debug_count <= 3:
                print(f"🧮 Distance calc #{self._debug_count}: ({lat1:.6f},{lon1:.6f}) to ({lat2:.6f},{lon2:.6f}) = {distance:.3f}km")
            
            return distance
            
        except Exception as e:
            print(f"❌ Error in distance calculation: {e}")
            return 999.0
    
    def _calculate_centroid(self, geometry):
        """Calculate centroid of geometry."""
        try:
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates')
            
            if geom_type == 'Point':
                return coordinates
            
            elif geom_type == 'Polygon' and coordinates:
                exterior = coordinates[0]
                if exterior:
                    avg_x = sum(coord[0] for coord in exterior) / len(exterior)
                    avg_y = sum(coord[1] for coord in exterior) / len(exterior)
                    return [avg_x, avg_y]
            
            return None
            
        except Exception:
            return None


class PDOKMapDisplayTool(Tool):
    """
    Format filtered PDOK data for map display with proper descriptions and metadata.
    """
    
    name = "format_pdok_for_map"
    description = "Format filtered PDOK data into proper map display format with descriptions"
    inputs = {
        "filtered_data": {"type": "object", "description": "Filtered data from PDOKDataFilterTool"},
        "location_name": {"type": "string", "description": "Name of the searched location"},
        "search_description": {"type": "string", "description": "Description of what was searched for"}
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, filtered_data, location_name, search_description):
        """Format filtered data for map display."""
        try:
            if not isinstance(filtered_data, dict) or 'filtered_features' not in filtered_data:
                return {"error": "Invalid filtered data format"}
            
            features = filtered_data['filtered_features']
            
            if not features:
                return {
                    "text_description": f"❌ No buildings found matching your criteria in {location_name}. {search_description}",
                    "geojson_data": []
                }
            
            # Process features for map display
            map_features = []
            
            for i, feature in enumerate(features):
                try:
                    properties = feature.get('properties', {})
                    
                    # Create feature name
                    feature_id = properties.get('identificatie', f'Feature_{i+1}')
                    building_year = feature.get('building_year') or properties.get('bouwjaar')
                    
                    feature_name = f"Building {feature_id[-6:]}" if len(feature_id) > 6 else feature_id
                    if building_year:
                        feature_name += f" ({building_year})"
                    
                    # Create description
                    desc_parts = []
                    
                    distance_km = feature.get('distance_km')
                    if distance_km is not None:
                        desc_parts.append(f"Distance: {distance_km:.3f}km")
                    
                    if building_year:
                        age = 2024 - building_year
                        desc_parts.append(f"Built: {building_year} ({age} years old)")
                    
                    status = properties.get('status')
                    if status:
                        desc_parts.append(f"Status: {status}")
                    
                    area_m2 = feature.get('area_m2') or properties.get('oppervlakte_min')
                    if area_m2:
                        desc_parts.append(f"Area: {area_m2:.0f}m²")
                    
                    units = properties.get('aantal_verblijfsobjecten')
                    if units:
                        desc_parts.append(f"Units: {units}")
                    
                    description = " | ".join(desc_parts) if desc_parts else "Building information"
                    
                    # Create map feature
                    map_feature = {
                        "name": feature_name,
                        "lat": float(feature.get('lat', 0)),
                        "lon": float(feature.get('lon', 0)),
                        "description": description,
                        "geometry": feature.get('geometry', {}),
                        "properties": {
                            **properties,
                            "distance_km": distance_km,
                            "building_year": building_year,
                            "area_m2": area_m2,
                            "centroid_lat": float(feature.get('lat', 0)),
                            "centroid_lon": float(feature.get('lon', 0))
                        }
                    }
                    
                    map_features.append(map_feature)
                    
                except Exception as e:
                    print(f"Error formatting feature {i+1}: {e}")
                    continue
            
            # Create text description
            text_description = self._create_text_description(
                map_features, location_name, search_description, filtered_data
            )
            
            return {
                "text_description": text_description,
                "geojson_data": map_features
            }
            
        except Exception as e:
            return {"error": f"Formatting error: {str(e)}"}
    
    def _create_text_description(self, features, location_name, search_description, filter_info):
        """Create detailed text description."""
        if not features:
            return f"❌ No features found in {location_name}. {search_description}"
        
        text_parts = []
        text_parts.append(f"## Buildings in {location_name}")
        text_parts.append(f"\nI found **{len(features)} buildings** in {location_name} matching your criteria: {search_description}")
        
        # Add filter information
        filters_applied = filter_info.get('filters_applied', {})
        filter_desc = []
        
        if filters_applied.get('max_distance_km'):
            filter_desc.append(f"within {filters_applied['max_distance_km']}km")
        
        if filters_applied.get('min_year') or filters_applied.get('max_year'):
            if filters_applied.get('max_year'):
                age = 2024 - filters_applied['max_year']
                filter_desc.append(f"older than {age} years (built before {filters_applied['max_year'] + 1})")
        
        if filter_desc:
            text_parts.append(f"**Filters applied**: {', '.join(filter_desc)}")
        
        # Add statistics
        years = [f.get('properties', {}).get('bouwjaar') for f in features if f.get('properties', {}).get('bouwjaar')]
        areas = [f.get('properties', {}).get('area_m2', 0) for f in features if f.get('properties', {}).get('area_m2', 0) > 0]
        distances = [f.get('properties', {}).get('distance_km') for f in features if f.get('properties', {}).get('distance_km')]
        
        if years:
            min_year = min(years)
            max_year = max(years)
            avg_year = sum(years) / len(years)
            text_parts.append(f"\n**Construction period**: {min_year} to {max_year} (average: {avg_year:.0f})")
        
        if areas:
            total_area = sum(areas)
            avg_area = sum(areas) / len(areas)
            text_parts.append(f"**Total building area**: {total_area:,.0f}m² (average: {avg_area:.0f}m²)")
        
        if distances:
            min_distance = min(distances)
            max_distance = max(distances)
            avg_distance = sum(distances) / len(distances)
            text_parts.append(f"**Distance range**: {min_distance:.3f}km to {max_distance:.3f}km (average: {avg_distance:.3f}km)")
        
        # Add sample buildings
        sort_method = filter_info.get('sorted_by', 'distance')
        if sort_method == 'distance':
            text_parts.append(f"\n**Closest buildings to {location_name}**:")
        elif sort_method == 'age' or sort_method == 'year':
            text_parts.append(f"\n**Buildings by age (oldest first)**:")
        else:
            text_parts.append(f"\n**Sample buildings found**:")
        
        for i, feature in enumerate(features[:5]):
            props = feature.get('properties', {})
            year = props.get('bouwjaar', 'Unknown year')
            area = props.get('area_m2', 0)
            distance = props.get('distance_km')
            
            desc = f"* **{feature['name']}**"
            if distance is not None:
                desc += f" - {distance:.3f}km away"
            if year != 'Unknown year':
                age = 2024 - year if isinstance(year, int) else 'Unknown'
                desc += f", Built {year} ({age} years old)"
            if area > 0:
                desc += f", {area:.0f}m²"
            
            text_parts.append(desc)
        
        text_parts.append(f"\nAll **{len(features)} buildings** are displayed on the map. Click any building for detailed information.")
        
        return "\n".join(text_parts)


# Usage example and integration with existing app.py
def create_enhanced_pdok_workflow():
    """
    Example of how to use the new modular PDOK tools together.
    This replaces the single monolithic PDOKBuildingsRealTool.
    """
    
    # Step 1: Discover services
    discovery_tool = PDOKServiceDiscoveryTool()
    services = discovery_tool.forward("bag")
    
    # Step 2: Make data request
    request_tool = PDOKDataRequestTool()
    raw_data = request_tool.forward(
        service_url="https://service.pdok.nl/lv/bag/wfs/v2_0",
        layer_name="bag:pand",
        center_lat=53.222229,
        center_lon=6.563343,
        radius_km=5.0,
        max_features=200
    )
    
    # Step 3: Filter data
    filter_tool = PDOKDataFilterTool()
    filtered_data = filter_tool.forward(
        features=raw_data,
        center_lat=53.222229,
        center_lon=6.563343,
        max_distance_km=5.0,
        max_year=1970,  # Buildings older than ~50 years
        sort_by="distance",
        limit=20
    )
    
    # Step 4: Format for map display
    display_tool = PDOKMapDisplayTool()
    final_result = display_tool.forward(
        filtered_data=filtered_data,
        location_name="Groningen",
        search_description="buildings older than 50 years within 5km"
    )
    
    return final_result


class PDOKBuildingsFlexibleTool(Tool):
    """
    Simplified combined tool that uses the modular approach internally.
    This provides a single interface for the agent while using the flexible tools behind the scenes.
    """
    
    name = "get_pdok_buildings_flexible"
    description = "Get PDOK buildings using flexible modular approach with better filtering and distance calculation"
    inputs = {
        "location": {"type": "string", "description": "Location name (e.g., 'Groningen', 'Amsterdam train station')"},
        "max_features": {"type": "integer", "description": "Maximum buildings to return (default: 20)", "nullable": True},
        "min_year": {"type": "integer", "description": "Minimum construction year", "nullable": True},
        "max_year": {"type": "integer", "description": "Maximum construction year", "nullable": True},
        "radius_km": {"type": "number", "description": "Search radius in kilometers (default: 5.0)", "nullable": True},
        "min_area_m2": {"type": "number", "description": "Minimum building area in m²", "nullable": True},
        "max_area_m2": {"type": "number", "description": "Maximum building area in m²", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.request_tool = PDOKDataRequestTool()
        self.filter_tool = PDOKDataFilterTool()
        self.display_tool = PDOKMapDisplayTool()
    
    def forward(self, location, max_features=20, min_year=None, max_year=None, 
                radius_km=5.0, min_area_m2=None, max_area_m2=None):
        """Get buildings using the flexible modular approach."""
        
        try:
            print(f"\n🏗️ === FLEXIBLE PDOK BUILDINGS SEARCH ===")
            print(f"Location: {location}")
            print(f"Max features: {max_features}")
            print(f"Search radius: {radius_km}km")
            
            # Step 1: Get location coordinates
            from tools.pdok_location import find_location_coordinates
            loc_data = find_location_coordinates(location)
            
            if "error" in loc_data:
                return {
                    "text_description": f"❌ Could not find location: {location}. {loc_data['error']}",
                    "geojson_data": [],
                    "error": loc_data["error"]
                }
            
            target_lat, target_lon = loc_data["lat"], loc_data["lon"]
            print(f"✅ Target location: {target_lat:.6f}, {target_lon:.6f}")
            
            # Step 2: Request raw data with larger buffer
            print("🌐 Requesting building data from PDOK BAG...")
            raw_data = self.request_tool.forward(
                service_url="https://service.pdok.nl/lv/bag/wfs/v2_0",
                layer_name="bag:pand",
                center_lat=target_lat,
                center_lon=target_lon,
                radius_km=radius_km * 1.2,  # Get more candidates
                max_features=max_features * 10  # Get more candidates for filtering
            )
            
            if raw_data.get('error'):
                return {
                    "text_description": f"❌ Error requesting data: {raw_data['error']}",
                    "geojson_data": [],
                    "error": raw_data['error']
                }
            
            print(f"📦 Received {raw_data.get('count', 0)} raw features")
            
            # Step 3: Apply filters
            print("🔽 Applying filters...")
            filtered_data = self.filter_tool.forward(
                features=raw_data,
                center_lat=target_lat,
                center_lon=target_lon,
                max_distance_km=radius_km,
                min_year=min_year,
                max_year=max_year,
                min_area_m2=min_area_m2,
                max_area_m2=max_area_m2,
                sort_by="distance",
                limit=max_features
            )
            
            if filtered_data.get('error'):
                return {
                    "text_description": f"❌ Error filtering data: {filtered_data['error']}",
                    "geojson_data": [],
                    "error": filtered_data['error']
                }
            
            print(f"📊 Filtered to {filtered_data.get('count', 0)} features")
            
            # Step 4: Format for display
            search_desc_parts = []
            if min_year or max_year:
                if max_year:
                    age = 2024 - max_year
                    search_desc_parts.append(f"older than {age} years")
                if min_year:
                    search_desc_parts.append(f"newer than {2024 - min_year} years")
            
            if min_area_m2 or max_area_m2:
                if min_area_m2:
                    search_desc_parts.append(f"larger than {min_area_m2}m²")
                if max_area_m2:
                    search_desc_parts.append(f"smaller than {max_area_m2}m²")
            
            search_description = ", ".join(search_desc_parts) if search_desc_parts else "any age/size"
            search_description += f" within {radius_km}km"
            
            final_result = self.display_tool.forward(
                filtered_data=filtered_data,
                location_name=loc_data.get('name', location),
                search_description=search_description
            )
            
            if final_result.get('error'):
                return {
                    "text_description": f"❌ Error formatting data: {final_result['error']}",
                    "geojson_data": [],
                    "error": final_result['error']
                }
            
            print(f"✅ Successfully created response with {len(final_result.get('geojson_data', []))} buildings")
            
            return final_result
            
        except Exception as e:
            error_msg = f"Flexible PDOK tool error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error retrieving buildings around {location}: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }


# Export the tools for use in app.py
__all__ = [
    "PDOKServiceDiscoveryTool",
    "PDOKDataRequestTool", 
    "PDOKDataFilterTool",
    "PDOKMapDisplayTool",
    "PDOKBuildingsFlexibleTool"
]