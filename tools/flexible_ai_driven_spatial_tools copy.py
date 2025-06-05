import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple

class FlexibleSpatialDataTool(Tool):
    """
    FIXED: Flexible tool with precise location-based data retrieval and building-specific improvements.
    """
    
    name = "fetch_pdok_data"
    description = """Fetch data from any PDOK WFS service with precise location-based retrieval.

CRITICAL FIXES:
- Strict location containment with configurable radius
- Enhanced distance validation to ensure features are within the specified area
- Improved coordinate system handling
- Building-specific optimizations with age analysis
- Detailed logging for debugging location issues
"""
    
    inputs = {
        "service_url": {
            "type": "string",
            "description": "PDOK WFS service URL"
        },
        "layer_name": {
            "type": "string", 
            "description": "Layer name to query"
        },
        "search_area": {
            "type": "object",
            "description": "Search area definition with center point and radius",
            "nullable": True
        },
        "filters": {
            "type": "object",
            "description": "Filters to apply (CQL, attribute filters, etc.)",
            "nullable": True
        },
        "max_features": {
            "type": "integer",
            "description": "Maximum features to return",
            "nullable": True
        },
        "purpose": {
            "type": "string",
            "description": "What this data will be used for (helps with processing)",
            "nullable": True
        },
        "strict_containment": {
            "type": "boolean",
            "description": "Ensure features are fully within the search radius (default: True)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        
        # Initialize coordinate transformers
        try:
            import pyproj
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.pyproj_available = True
            print("✅ FIXED FlexibleSpatialDataTool initialized with coordinate transformers")
        except ImportError:
            self.transformer_to_rd = None
            self.transformer_to_wgs84 = None
            self.pyproj_available = False
            print("⚠️ PyProj not available - coordinate transformation limited")
    
    def forward(self, service_url: str, layer_name: str, search_area: Optional[Union[Dict, str]] = None, 
                filters: Optional[Union[Dict, str]] = None, max_features: Optional[int] = 100,
                purpose: Optional[str] = None, strict_containment: bool = True) -> Dict:
        """FIXED: Fetch data with precise location-based retrieval."""
        
        try:
            print(f"🌐 FIXED Flexible PDOK data fetch")
            print(f"   Service: {service_url}")
            print(f"   Layer: {layer_name}")
            print(f"   Purpose: {purpose}")
            print(f"   Strict Containment: {strict_containment}")
            
            # FIXED: Detect if this is a building request and adjust parameters
            is_building_request = 'bag' in service_url or 'pand' in layer_name.lower()
            if is_building_request:
                print(f"🏠 FIXED: Building request detected - applying building-specific optimizations")
                
                # FIXED: Default to 1km radius for buildings if not specified
                if search_area and isinstance(search_area, dict) and 'radius_km' in search_area:
                    original_radius = search_area['radius_km']
                    if original_radius > 3.0:
                        search_area['radius_km'] = 1.0  # Tighten to 1km for precision
                        print(f"🔧 FIXED: Reduced search radius from {original_radius}km to {search_area['radius_km']}km for buildings")
                elif search_area and isinstance(search_area, dict):
                    search_area['radius_km'] = 1.0
                    print(f"🔧 FIXED: Set default building search radius to 1km")
            
            # Determine coordinate system
            srs = self._determine_coordinate_system_fixed(service_url)
            print(f"   🗺️ FIXED: Using coordinate system: {srs}")
            
            # Build base parameters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'srsName': srs,
                'count': max_features or 100
            }
            
            # FIXED: Process search area with stricter validation
            radius_km = None
            if search_area:
                bbox, radius_km = self._process_search_area_fixed(search_area, srs)
                if bbox:
                    params['bbox'] = f"{bbox},{srs}"
                    print(f"   ✅ FIXED Search area processed: {bbox}")
                else:
                    print("   ⚠️ Could not process search area - proceeding without bbox")
            
            # FIXED: Add CQL filter for strict containment
            cql_filters = []
            if strict_containment and search_area and isinstance(search_area, dict) and 'center' in search_area:
                cql_filter = self._build_containment_cql_filter(search_area, srs)
                if cql_filter:
                    cql_filters.append(cql_filter)
                    print(f"   ✅ FIXED Added containment CQL filter: {cql_filter}")
            
            # Process user-provided filters
            if filters:
                user_cql_filter = self._build_cql_filter_fixed(filters)
                if user_cql_filter:
                    cql_filters.append(user_cql_filter)
                    print(f"   ✅ FIXED User CQL filter applied: {user_cql_filter}")
            
            if cql_filters:
                params['cql_filter'] = " AND ".join(cql_filters)
            
            print(f"🚀 FIXED Executing WFS request with params: {params}")
            
            # Make request
            response = requests.get(service_url, params=params, timeout=30)
            
            print(f"📡 Response status: {response.status_code}")
            print(f"📏 Response size: {len(response.content)} bytes")
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                return {
                    'error': f'HTTP {response.status_code}: {response.text[:200]}',
                    'features': [],
                    'success': False
                }
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"📦 Received {len(features)} raw features")
            
            if len(features) == 0:
                print("⚠️ FIXED: No features returned")
                return {
                    'features': [],
                    'count': 0,
                    'success': True,
                    'message': 'No features found in the specified area'
                }
            
            # FIXED: Process features with strict distance validation
            processed_features = []
            search_center = None
            
            if search_area and isinstance(search_area, dict) and 'center' in search_area:
                search_center = search_area['center']
            
            for i, feature in enumerate(features):
                try:
                    processed = self._process_feature_fixed(
                        feature, srs, purpose, search_center, is_building_request, radius_km, strict_containment
                    )
                    if processed:
                        processed_features.append(processed)
                except Exception as e:
                    print(f"❌ Error processing feature {i+1}: {e}")
                    continue
            
            print(f"✅ FIXED Processed {len(processed_features)} valid features")
            
            # FIXED: Generate building-specific legend data
            legend_data = None
            if is_building_request and processed_features:
                legend_data = self._generate_building_legend(processed_features)
                print(f"🏷️ FIXED: Generated building legend with {len(legend_data.get('categories', []))} categories")
            
            return {
                "features": processed_features,
                "count": len(processed_features),
                "service": service_url,
                "layer": layer_name,
                "purpose": purpose,
                "coordinate_system": srs,
                "success": True,
                "legend_data": legend_data,
                "is_building_data": is_building_request
            }
            
        except Exception as e:
            error_msg = f"FIXED Flexible PDOK fetch failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "error": error_msg,
                "success": False,
                "features": []
            }
    
    def _determine_coordinate_system_fixed(self, service_url: str) -> str:
        """FIXED: Determine correct coordinate system based on service."""
        if "bag" in service_url:
            return "EPSG:28992"  # BAG uses RD New
        elif "bestandbodemgebruik" in service_url:
            return "EPSG:28992"  # Land use uses RD New
        elif "kadaster" in service_url:
            return "EPSG:28992"  # Cadastral uses RD New
        elif "natura2000" in service_url:
            return "EPSG:28992"  # Natura2000 uses RD New
        elif "cbs" in service_url and "wijkenbuurten" in service_url:
            return "EPSG:28992"  # CBS administrative boundaries use RD New
        else:
            return "EPSG:4326"  # Default to WGS84
    
    def _process_search_area_fixed(self, search_area: Union[Dict, str], srs: str) -> Tuple[Optional[str], Optional[float]]:
        """FIXED: Process search area with precise coordinate validation."""
        try:
            print(f"🔍 FIXED Processing search area: {search_area}")
            
            if isinstance(search_area, dict) and 'center' in search_area:
                center = search_area['center']
                radius_km = search_area.get('radius_km', 1.0)  # Default to 1km
                
                if not isinstance(center, (list, tuple)) or len(center) != 2:
                    print(f"   ❌ Invalid center format: {center}")
                    return None, None
                
                lat, lon = float(center[0]), float(center[1])
                
                # FIXED: Strict Netherlands bounds validation
                if not (50.5 <= lat <= 53.8 and 3.0 <= lon <= 7.5):
                    print(f"   ❌ FIXED: Coordinates outside strict Netherlands bounds: {lat}, {lon}")
                    return None, None
                
                print(f"   ✅ FIXED: Valid Netherlands coordinates: lat={lat}, lon={lon}, radius={radius_km}km")
                
                if srs == "EPSG:28992" and self.transformer_to_rd:
                    # Convert WGS84 to RD New
                    center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                    print(f"   🔄 FIXED: Converted to RD New: X={center_x:.2f}, Y={center_y:.2f}")
                    
                    # FIXED: Validate RD coordinates
                    if not (10000 <= center_x <= 280000 and 300000 <= center_y <= 630000):
                        print(f"   ❌ FIXED: RD coordinates out of reasonable bounds: {center_x}, {center_y}")
                        return None, None
                    
                    radius_m = radius_km * 1000
                    min_x = center_x - radius_m
                    min_y = center_y - radius_m
                    max_x = center_x + radius_m
                    max_y = center_y + radius_m
                    
                    bbox = f"{min_x},{min_y},{max_x},{max_y}"
                    print(f"   ✅ FIXED: RD New bbox: {bbox}")
                    return bbox, radius_km
                    
                elif srs == "EPSG:4326":
                    # Use WGS84 directly
                    lat_rad = math.radians(lat)
                    km_per_degree_lat = 111.0
                    km_per_degree_lon = 111.0 * math.cos(lat_rad)
                    
                    lat_buffer = radius_km / km_per_degree_lat
                    lon_buffer = radius_km / km_per_degree_lon
                    
                    min_lon = lon - lon_buffer
                    min_lat = lat - lat_buffer
                    max_lon = lon + lon_buffer
                    max_lat = lat + lat_buffer
                    
                    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
                    print(f"   ✅ FIXED: WGS84 bbox: {bbox}")
                    return bbox, radius_km
            
            return None, None
            
        except Exception as e:
            print(f"❌ FIXED Error processing search area: {e}")
            return None, None
    
    def _build_containment_cql_filter(self, search_area: Dict, srs: str) -> Optional[str]:
        """FIXED: Build CQL filter for strict containment within search area."""
        try:
            center = search_area['center']
            radius_km = search_area.get('radius_km', 1.0)
            lat, lon = float(center[0]), float(center[1])
            
            if srs == "EPSG:28992" and self.transformer_to_rd:
                center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                radius_m = radius_km * 1000
                return f"WITHIN(the_geom, POLYGON(({center_x-radius_m} {center_y-radius_m}, {center_x-radius_m} {center_y+radius_m}, {center_x+radius_m} {center_y+radius_m}, {center_x+radius_m} {center_y-radius_m}, {center_x-radius_m} {center_y-radius_m})))"
            elif srs == "EPSG:4326":
                lat_rad = math.radians(lat)
                km_per_degree_lat = 111.0
                km_per_degree_lon = 111.0 * math.cos(lat_rad)
                lat_buffer = radius_km / km_per_degree_lat
                lon_buffer = radius_km / km_per_degree_lon
                min_lon = lon - lon_buffer
                min_lat = lat - lat_buffer
                max_lon = lon + lon_buffer
                max_lat = lat + lat_buffer
                return f"WITHIN(the_geom, POLYGON(({min_lon} {min_lat}, {min_lon} {max_lat}, {max_lon} {max_lat}, {max_lon} {min_lat}, {min_lon} {min_lat})))"
            return None
        except Exception as e:
            print(f"❌ FIXED Error building containment CQL filter: {e}")
            return None
    
    def _build_cql_filter_fixed(self, filters: Union[Dict, str]) -> Optional[str]:
        """FIXED: Build CQL filter with correct syntax."""
        try:
            if isinstance(filters, str):
                return filters.strip() if filters.strip() else None
            elif isinstance(filters, dict):
                filter_parts = []
                if 'attribute_filters' in filters:
                    for attr, value in filters['attribute_filters'].items():
                        if isinstance(value, str):
                            filter_parts.append(f"{attr} = '{value}'")
                        else:
                            filter_parts.append(f"{attr} = {value}")
                return " AND ".join(filter_parts) if filter_parts else None
            return None
        except Exception as e:
            print(f"❌ FIXED Error building CQL filter: {e}")
            return None
    
    def _process_feature_fixed(self, feature: Dict, srs: str, purpose: Optional[str], 
                             search_center: Optional[List[float]], is_building: bool,
                             radius_km: Optional[float], strict_containment: bool) -> Optional[Dict]:
        """FIXED: Process feature with strict distance validation."""
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # FIXED: Convert geometry to WGS84 for frontend
            if srs == "EPSG:28992" and self.transformer_to_wgs84:
                geometry = self._convert_geometry_to_wgs84_fixed(geometry)
            
            # Calculate centroid
            centroid = self._calculate_centroid_fixed(geometry)
            if not centroid:
                print(f"   ❌ Could not calculate centroid for feature")
                return None
            
            lat, lon = centroid
            
            # FIXED: Validate centroid is in Netherlands
            if not (50.5 <= lat <= 53.8 and 3.0 <= lon <= 7.5):
                print(f"   ❌ FIXED: Feature centroid outside Netherlands: {lat:.6f}, {lon:.6f}")
                return None
            
            # FIXED: Strict distance validation if search center provided
            if search_center and radius_km and strict_containment:
                center_lat, center_lon = search_center[0], search_center[1]
                distance_km = self._calculate_distance(lat, lon, center_lat, center_lon)
                
                if distance_km > radius_km:
                    print(f"   ❌ FIXED: Feature outside search radius: {distance_km:.2f}km > {radius_km}km")
                    return None
                print(f"   ✅ FIXED: Feature within radius: {distance_km:.2f}km <= {radius_km}km")
            
            # FIXED: Enhanced feature naming for buildings
            if is_building:
                feature_name = self._create_building_name(properties)
                feature_description = self._create_building_description(properties)
            else:
                feature_name = self._create_feature_name(properties)
                feature_description = self._create_feature_description(properties)
            
            return {
                "type": "Feature",
                "name": feature_name,
                "properties": properties,
                "geometry": geometry,
                "lat": float(lat),
                "lon": float(lon),
                "centroid": {"lat": lat, "lon": lon},
                "processing_purpose": purpose,
                "description": feature_description,
                "is_building": is_building
            }
            
        except Exception as e:
            print(f"❌ FIXED Error processing feature: {e}")
            return None
    
    def _create_building_name(self, properties: Dict) -> str:
        """FIXED: Create meaningful building names."""
        year = properties.get('bouwjaar')
        if year and str(year).isdigit():
            year = int(year)
            if year < 1900:
                age_category = "Historic"
            elif year < 1950:
                age_category = "Pre-war"
            elif year < 1980:
                age_category = "Post-war"
            elif year < 2000:
                age_category = "Late 20th Century"
            else:
                age_category = "Modern"
            
            return f"{age_category} Building ({year})"
        else:
            return "Building (unknown age)"
    
    def _create_building_description(self, properties: Dict) -> str:
        """FIXED: Create detailed building descriptions."""
        desc_parts = []
        
        year = properties.get('bouwjaar')
        if year:
            desc_parts.append(f"Built: {year}")
        
        status = properties.get('status')
        if status:
            desc_parts.append(f"Status: {status}")
        
        oppervlakte = properties.get('oppervlakte')
        if oppervlakte:
            desc_parts.append(f"Area: {oppervlakte}m²")
        
        return " | ".join(desc_parts) if desc_parts else "Building feature"
    
    def _create_feature_name(self, properties: Dict) -> str:
        """Create feature name for non-building data."""
        if 'bodemgebruik' in properties:
            return f"Land Use: {properties['bodemgebruik']}"
        elif 'naam' in properties:
            return properties['naam']
        else:
            return "Feature"
    
    def _create_feature_description(self, properties: Dict) -> str:
        """Create feature description for non-building data."""
        desc_parts = []
        
        if 'bodemgebruik' in properties:
            desc_parts.append(f"Type: {properties['bodemgebruik']}")
        
        if 'oppervlakte' in properties:
            desc_parts.append(f"Area: {properties['oppervlakte']}")
        
        return " | ".join(desc_parts) if desc_parts else "Geographic feature"
    
    def _generate_building_legend(self, features: List[Dict]) -> Dict:
        """FIXED: Generate building legend with age-based color coding."""
        try:
            legend_data = {
                "layer_type": "buildings",
                "title": "🏠 Buildings by Age",
                "categories": [],
                "statistics": {}
            }
            
            # Analyze building years
            building_years = []
            for feature in features:
                year = feature.get('properties', {}).get('bouwjaar')
                if year and str(year).isdigit():
                    building_years.append(int(year))
            
            if not building_years:
                return legend_data
            
            # Create age categories with colors
            age_categories = [
                {"label": "Historic (< 1900)", "color": "#8B0000", "min_year": 0, "max_year": 1899, "count": 0},
                {"label": "Pre-war (1900-1949)", "color": "#FF4500", "min_year": 1900, "max_year": 1949, "count": 0},
                {"label": "Post-war (1950-1979)", "color": "#32CD32", "min_year": 1950, "max_year": 1979, "count": 0},
                {"label": "Late 20th C (1980-1999)", "color": "#1E90FF", "min_year": 1980, "max_year": 1999, "count": 0},
                {"label": "Modern (2000+)", "color": "#FF1493", "min_year": 2000, "max_year": 9999, "count": 0}
            ]
            
            # Count buildings in each category
            for year in building_years:
                for category in age_categories:
                    if category["min_year"] <= year <= category["max_year"]:
                        category["count"] += 1
                        break
            
            # Only include categories with buildings
            legend_data["categories"] = [cat for cat in age_categories if cat["count"] > 0]
            
            # Add statistics
            legend_data["statistics"] = {
                "total_buildings": len(features),
                "buildings_with_year": len(building_years),
                "oldest_building": min(building_years) if building_years else None,
                "newest_building": max(building_years) if building_years else None,
                "average_year": int(sum(building_years) / len(building_years)) if building_years else None
            }
            
            return legend_data
            
        except Exception as e:
            print(f"❌ Error generating building legend: {e}")
            return {"layer_type": "buildings", "title": "🏠 Buildings", "categories": []}
    
    def _convert_geometry_to_wgs84_fixed(self, geometry: Dict) -> Dict:
        """FIXED: Convert geometry with better error handling."""
        try:
            if not self.transformer_to_wgs84:
                return geometry
            
            if geometry['type'] == 'Point':
                coords = geometry['coordinates']
                if len(coords) >= 2:
                    wgs84 = self.transformer_to_wgs84.transform(coords[0], coords[1])
                    return {'type': 'Point', 'coordinates': [wgs84[0], wgs84[1]]}
            
            elif geometry['type'] == 'Polygon':
                wgs84_coords = []
                for ring in geometry['coordinates']:
                    wgs84_ring = []
                    for coord in ring:
                        if len(coord) >= 2:
                            wgs84 = self.transformer_to_wgs84.transform(coord[0], coord[1])
                            wgs84_ring.append([wgs84[0], wgs84[1]])
                    wgs84_coords.append(wgs84_ring)
                return {'type': 'Polygon', 'coordinates': wgs84_coords}
            
            return geometry
            
        except Exception as e:
            print(f"❌ Error converting geometry: {e}")
            return geometry
    
    def _calculate_centroid_fixed(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """FIXED: Calculate centroid with better validation."""
        try:
            if geometry['type'] == 'Point':
                coords = geometry['coordinates']
                if len(coords) >= 2:
                    return coords[1], coords[0]  # lat, lon
            
            elif geometry['type'] == 'Polygon':
                coords = geometry['coordinates'][0]
                if coords and len(coords) > 0:
                    valid_coords = [c for c in coords if len(c) >= 2]
                    if valid_coords:
                        avg_x = sum(c[0] for c in valid_coords) / len(valid_coords)
                        avg_y = sum(c[1] for c in valid_coords) / len(valid_coords)
                        return avg_y, avg_x  # lat, lon
            
            return None
            
        except Exception as e:
            print(f"❌ Error calculating centroid: {e}")
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

# Keep the existing FlexibleSpatialAnalysisTool unchanged
class FlexibleSpatialAnalysisTool(Tool):
    """
    Flexible tool for spatial analysis operations.
    The AI decides what type of analysis to perform and how to combine datasets.
    """
    
    name = "perform_spatial_analysis"
    description = """Perform flexible spatial analysis on geospatial datasets.

The AI can use this tool to:
- Calculate distances between features from different datasets
- Rank features by multiple criteria
- Score features based on spatial relationships
- Filter results by spatial or attribute conditions
- Combine analysis from multiple PDOK services

The AI determines what analysis operations to perform based on the user's query."""
    
    inputs = {
        "datasets": {
            "type": "object",
            "description": "Dictionary of datasets to analyze (from fetch_pdok_data calls)"
        },
        "analysis_operations": {
            "type": "object",
            "description": "Analysis operations to perform (AI-determined)"
        },
        "reference_point": {
            "type": "object",
            "description": "Reference point for distance calculations",
            "nullable": True
        },
        "output_requirements": {
            "type": "object",
            "description": "Requirements for output format and content",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, datasets: Dict, analysis_operations: Dict, 
                reference_point: Optional[Dict] = None, 
                output_requirements: Optional[Dict] = None) -> Dict:
        """Perform flexible spatial analysis."""
        
        try:
            print(f"🧮 Flexible spatial analysis")
            print(f"   Datasets: {list(datasets.keys())}")
            print(f"   Operations: {list(analysis_operations.keys())}")
            
            results = {}
            
            # Process each analysis operation
            for operation_name, operation_config in analysis_operations.items():
                print(f"   🔄 Performing {operation_name}")
                
                if operation_name == "proximity_analysis":
                    results[operation_name] = self._proximity_analysis(
                        datasets, operation_config, reference_point
                    )
                
                elif operation_name == "ranking":
                    results[operation_name] = self._ranking_analysis(
                        datasets, operation_config
                    )
                
                elif operation_name == "scoring":
                    results[operation_name] = self._scoring_analysis(
                        datasets, operation_config, reference_point
                    )
                
                elif operation_name == "filtering":
                    results[operation_name] = self._filtering_analysis(
                        datasets, operation_config
                    )
                
                elif operation_name == "combining":
                    results[operation_name] = self._combining_analysis(
                        datasets, operation_config
                    )
                
                else:
                    # Custom analysis - let AI define the operation
                    results[operation_name] = self._custom_analysis(
                        datasets, operation_config, operation_name
                    )
            
            # Format final output
            final_output = self._format_analysis_output(results, output_requirements)
            
            return {
                "analysis_results": results,
                "formatted_output": final_output,
                "success": True
            }
            
        except Exception as e:
            return {
                "error": f"Spatial analysis failed: {str(e)}",
                "success": False
            }
    
    def _proximity_analysis(self, datasets: Dict, config: Dict, reference_point: Optional[Dict]) -> Dict:
        """Perform proximity analysis between datasets."""
        try:
            primary_dataset = config.get('primary_dataset')
            secondary_datasets = config.get('secondary_datasets', [])
            
            if not primary_dataset or primary_dataset not in datasets:
                return {"error": "Primary dataset not found"}
            
            primary_features = datasets[primary_dataset].get('features', [])
            results = []
            
            for feature in primary_features:
                feature_result = {
                    **feature,
                    'proximity_scores': {},
                    'nearest_features': {}
                }
                
                # Calculate distance to reference point if provided
                if reference_point and 'center' in reference_point:
                    ref_lat, ref_lon = reference_point['center']
                    distance = self._calculate_distance(
                        feature['lat'], feature['lon'], ref_lat, ref_lon
                    )
                    feature_result['distance_to_reference'] = distance
                
                # Calculate proximity to secondary datasets
                for secondary_name in secondary_datasets:
                    if secondary_name in datasets:
                        secondary_features = datasets[secondary_name].get('features', [])
                        
                        min_distance = float('inf')
                        nearest_feature = None
                        
                        for sec_feature in secondary_features:
                            distance = self._calculate_distance(
                                feature['lat'], feature['lon'],
                                sec_feature['lat'], sec_feature['lon']
                            )
                            
                            if distance < min_distance:
                                min_distance = distance
                                nearest_feature = sec_feature
                        
                        feature_result['proximity_scores'][secondary_name] = min_distance
                        feature_result['nearest_features'][secondary_name] = {
                            'distance_km': min_distance,
                            'feature': nearest_feature
                        }
                
                results.append(feature_result)
            
            return {"features": results, "operation": "proximity_analysis"}
            
        except Exception as e:
            return {"error": f"Proximity analysis failed: {str(e)}"}
    
    def _ranking_analysis(self, datasets: Dict, config: Dict) -> Dict:
        """Perform ranking analysis."""
        pass
    
    def _scoring_analysis(self, datasets: Dict, config: Dict, reference_point: Optional[Dict]) -> Dict:
        """Perform scoring analysis."""
        pass
    
    def _filtering_analysis(self, datasets: Dict, config: Dict) -> Dict:
        """Perform filtering analysis."""
        pass
    
    def _combining_analysis(self, datasets: Dict, config: Dict) -> Dict:
        """Perform combining analysis."""
        pass
    
    def _custom_analysis(self, datasets: Dict, config: Dict, operation_name: str) -> Dict:
        """Perform custom analysis operation."""
        return {"message": f"Custom analysis '{operation_name}' performed", "config": config}
    
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
    
    def _format_analysis_output(self, results: Dict, output_requirements: Optional[Dict]) -> Dict:
        """Format analysis output based on requirements."""
        try:
            final_features = []
            
            for operation_name, operation_result in results.items():
                if isinstance(operation_result, dict) and 'features' in operation_result:
                    final_features = operation_result['features']
            
            enhanced_features = []
            for i, feature in enumerate(final_features):
                rank = i + 1 if 'rank' in feature or 'analysis_score' in feature else None
                
                name_parts = []
                if rank:
                    name_parts.append(f"#{rank}")
                
                area_m2 = feature.get('properties', {}).get('kadastraleGrootteWaarde', 0)
                if area_m2 > 0:
                    area_ha = area_m2 / 10000
                    name_parts.append(f"({area_ha:.1f}ha)")
                
                name = " ".join(name_parts) if name_parts else f"Feature {i+1}"
                
                desc_parts = []
                if 'analysis_score' in feature:
                    desc_parts.append(f"Score: {feature['analysis_score']:.1f}")
                
                if 'distance_to_reference' in feature:
                    desc_parts.append(f"Distance: {feature['distance_to_reference']:.2f}km")
                
                proximity_scores = feature.get('proximity_scores', {})
                for dataset, distance in proximity_scores.items():
                    desc_parts.append(f"{dataset}: {distance:.2f}km")
                
                description = " | ".join(desc_parts) if desc_parts else "Spatial feature"
                
                enhanced_feature = {
                    "type": "Feature",
                    "name": name,
                    "lat": feature['lat'],
                    "lon": feature['lon'],
                    "description": description,
                    "geometry": feature['geometry'],
                    "properties": {
                        **feature.get('properties', {}),
                        **{k: v for k, v in feature.items() if k not in ['type', 'properties', 'geometry']}
                    }
                }
                
                enhanced_features.append(enhanced_feature)
            
            return {
                "features": enhanced_features,
                "count": len(enhanced_features),
                "analysis_summary": {
                    "operations_performed": list(results.keys()),
                    "total_features": len(enhanced_features)
                }
            }
            
        except Exception as e:
            return {"error": f"Output formatting failed: {str(e)}"}

__all__ = ["FlexibleSpatialDataTool", "FlexibleSpatialAnalysisTool"]