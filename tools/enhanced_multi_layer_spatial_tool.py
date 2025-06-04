# tools/enhanced_multi_layer_spatial_tool.py

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict

class MultiLayerSpatialAnalysisTool(Tool):
    """
    Enhanced tool for complex multi-layer spatial analysis that can:
    1. Query multiple PDOK services simultaneously
    2. Perform spatial proximity analysis
    3. Rank and score results based on multiple criteria
    4. Handle complex multi-step geospatial workflows
    """
    
    name = "analyze_multiple_spatial_layers"
    description = """Perform complex spatial analysis involving multiple PDOK layers.

This tool can handle queries that require:
- Multiple PDOK services (parcels + Natura 2000, buildings + protected areas, etc.)
- Spatial proximity analysis between different layer types
- Ranking and scoring based on size, distance, and other criteria
- Complex filtering across multiple datasets

Use this for questions like:
- "Find parcels >5ha near Natura 2000 areas around Amsterdam"
- "Show buildings suitable for solar panels near protected zones"
- "Rank parcels by size and proximity to environmental areas"
- "Find parcels close to both water and protected nature areas"

The tool automatically determines which PDOK services to use and performs the spatial analysis."""
    
    inputs = {
        "query_description": {
            "type": "string",
            "description": "Description of the spatial analysis needed"
        },
        "center_lat": {
            "type": "number",
            "description": "Center latitude for search area",
            "nullable": True
        },
        "center_lon": {
            "type": "number",
            "description": "Center longitude for search area", 
            "nullable": True
        },
        "search_radius_km": {
            "type": "number",
            "description": "Search radius in kilometers (default: 10)",
            "nullable": True
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum results to return (default: 50)",
            "nullable": True
        },
        "size_threshold_ha": {
            "type": "number",
            "description": "Size threshold in hectares for filtering",
            "nullable": True
        },
        "location_name": {
            "type": "string",
            "description": "Location name if coordinates not provided",
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
        except ImportError:
            self.transformer_to_rd = None
            self.transformer_to_wgs84 = None
            self.pyproj_available = False
        
        # Define multi-layer analysis patterns
        self.analysis_patterns = {
            "parcels_natura2000": {
                "services": ["cadastral", "natura2000"],
                "primary_layer": "kadastralekaart:Perceel",
                "secondary_layer": "natura2000:natura2000",
                "analysis_type": "proximity_ranking"
            },
            "buildings_solar_suitability": {
                "services": ["bag", "bgt"],
                "primary_layer": "bag:pand",
                "secondary_layer": "bgt:bouwwerk",
                "analysis_type": "area_centrality"
            },
            "parcels_water_natura": {
                "services": ["cadastral", "natura2000", "bgt"],
                "primary_layer": "kadastralekaart:Perceel",
                "secondary_layers": ["natura2000:natura2000", "bgt:waterdeel"],
                "analysis_type": "multi_proximity"
            },
            "environmental_impact": {
                "services": ["cadastral", "natura2000", "wetlands"],
                "primary_layer": "kadastralekaart:Perceel",
                "secondary_layers": ["natura2000:natura2000", "beschermdegebieden:protectedsite"],
                "analysis_type": "environmental_scoring"
            }
        }
        
        # Service configurations
        self.services = {
            "cadastral": {
                "url": "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0",
                "coordinate_system": "EPSG:28992",
                "area_attribute": "kadastraleGrootteWaarde"
            },
            "natura2000": {
                "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
                "coordinate_system": "EPSG:28992",
                "name_attribute": "naam"
            },
            "wetlands": {
                "url": "https://service.pdok.nl/rvo/beschermdegebieden/wetlands/wfs/v1_0",
                "coordinate_system": "EPSG:28992",
                "name_attribute": "naam"
            },
            "bag": {
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "coordinate_system": "EPSG:28992",
                "area_attribute": "oppervlakte"
            },
            "bgt": {
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                "coordinate_system": "EPSG:28992"
            }
        }
    
    def forward(self, query_description: str, center_lat: Optional[float] = None, 
                center_lon: Optional[float] = None, search_radius_km: Optional[float] = 10,
                max_results: Optional[int] = 50, size_threshold_ha: Optional[float] = None,
                location_name: Optional[str] = None) -> Dict:
        """Perform multi-layer spatial analysis."""
        
        try:
            print(f"🔍 Multi-layer spatial analysis: {query_description}")
            
            # Step 1: Determine analysis pattern
            analysis_pattern = self._determine_analysis_pattern(query_description)
            print(f"📋 Analysis pattern: {analysis_pattern['type']}")
            
            # Step 2: Get coordinates if needed
            if not center_lat or not center_lon:
                if location_name:
                    coords = self._search_location(location_name)
                    if coords.get('error'):
                        return coords
                    center_lat, center_lon = coords['lat'], coords['lon']
                else:
                    return {"error": "Either coordinates or location_name must be provided"}
            
            # Step 3: Convert to RD New
            if not self.pyproj_available:
                return {"error": "PyProj required for coordinate transformation"}
            
            center_x, center_y = self.transformer_to_rd.transform(center_lon, center_lat)
            bbox = self._create_bbox_rd(center_x, center_y, search_radius_km)
            
            print(f"📍 Center: {center_lat:.6f}, {center_lon:.6f} (RD: {center_x:.0f}, {center_y:.0f})")
            print(f"🗺️ Search radius: {search_radius_km}km, Bbox: {bbox}")
            
            # Step 4: Fetch data from multiple services
            datasets = {}
            for service_name in analysis_pattern['services']:
                print(f"📡 Fetching data from {service_name}...")
                service_data = self._fetch_service_data(
                    service_name, 
                    analysis_pattern.get('layers', {}).get(service_name),
                    bbox, 
                    size_threshold_ha
                )
                datasets[service_name] = service_data
                print(f"   ✅ {service_name}: {len(service_data.get('features', []))} features")
            
            # Step 5: Perform spatial analysis
            print(f"🧮 Performing {analysis_pattern['type']} analysis...")
            analysis_result = self._perform_spatial_analysis(
                datasets, 
                analysis_pattern, 
                center_lat, 
                center_lon,
                query_description
            )
            
            # Step 6: Rank and filter results
            ranked_results = self._rank_and_filter_results(
                analysis_result, 
                max_results, 
                analysis_pattern['type'],
                query_description
            )
            
            # Step 7: Format response
            return self._format_multi_layer_response(
                ranked_results, 
                datasets, 
                analysis_pattern, 
                query_description,
                center_lat,
                center_lon
            )
            
        except Exception as e:
            return {"error": f"Multi-layer analysis failed: {str(e)}"}
    
    def _determine_analysis_pattern(self, query: str) -> Dict:
        """Determine which analysis pattern to use based on query."""
        query_lower = query.lower()
        
        # Check for parcels + natura2000 pattern
        if any(word in query_lower for word in ['parcel', 'kadaster']) and 'natura' in query_lower:
            return {
                "type": "parcels_natura2000",
                "services": ["cadastral", "natura2000"],
                "layers": {
                    "cadastral": "kadastralekaart:Perceel",
                    "natura2000": "natura2000:natura2000"
                },
                "primary": "cadastral",
                "secondary": ["natura2000"]
            }
        
        # Check for solar suitability pattern
        elif any(word in query_lower for word in ['solar', 'roof', 'building']) and any(word in query_lower for word in ['suitable', 'central']):
            return {
                "type": "buildings_solar_suitability", 
                "services": ["bag"],
                "layers": {
                    "bag": "bag:pand"
                },
                "primary": "bag",
                "secondary": []
            }
        
        # Check for environmental impact pattern
        elif ('natura' in query_lower and any(word in query_lower for word in ['wetland', 'water', 'environment'])):
            return {
                "type": "environmental_impact",
                "services": ["cadastral", "natura2000", "wetlands"],
                "layers": {
                    "cadastral": "kadastralekaart:Perceel",
                    "natura2000": "natura2000:natura2000",
                    "wetlands": "beschermdegebieden:protectedsite"
                },
                "primary": "cadastral",
                "secondary": ["natura2000", "wetlands"]
            }
        
        # Default to parcels + natura2000 if parcels mentioned
        elif any(word in query_lower for word in ['parcel', 'kadaster']):
            return {
                "type": "parcels_natura2000",
                "services": ["cadastral", "natura2000"],
                "layers": {
                    "cadastral": "kadastralekaart:Perceel", 
                    "natura2000": "natura2000:natura2000"
                },
                "primary": "cadastral",
                "secondary": ["natura2000"]
            }
        
        # Default fallback
        else:
            return {
                "type": "general_proximity",
                "services": ["cadastral"],
                "layers": {
                    "cadastral": "kadastralekaart:Perceel"
                },
                "primary": "cadastral",
                "secondary": []
            }
    
    def _search_location(self, location_name: str) -> Dict:
        """Search for location coordinates using PDOK Locatieserver."""
        try:
            url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
            params = {
                'q': location_name,
                'rows': 1,
                'fl': 'weergavenaam,centroide_ll',
                'fq': 'type:(adres OR woonplaats OR gemeente)',
                'wt': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if not docs:
                return {"error": f"Location not found: {location_name}"}
            
            centroide = docs[0].get('centroide_ll', '')
            if 'POINT(' in centroide:
                coords = centroide.replace('POINT(', '').replace(')', '').split()
                lon, lat = float(coords[0]), float(coords[1])
                return {"lat": lat, "lon": lon, "name": docs[0].get('weergavenaam', location_name)}
            
            return {"error": f"Could not parse coordinates for {location_name}"}
            
        except Exception as e:
            return {"error": f"Location search failed: {str(e)}"}
    
    def _create_bbox_rd(self, center_x: float, center_y: float, radius_km: float) -> str:
        """Create bounding box in RD New coordinates."""
        radius_m = radius_km * 1000
        min_x = center_x - radius_m
        min_y = center_y - radius_m
        max_x = center_x + radius_m
        max_y = center_y + radius_m
        return f"{min_x},{min_y},{max_x},{max_y}"
    
    def _fetch_service_data(self, service_name: str, layer_name: str, bbox: str, size_threshold_ha: Optional[float]) -> Dict:
        """Fetch data from a specific PDOK service."""
        try:
            service_config = self.services[service_name]
            
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'srsName': service_config['coordinate_system'],
                'bbox': f"{bbox},{service_config['coordinate_system']}",
                'count': 1000  # Get more features for analysis
            }
            
            # Add size filter if applicable and threshold provided
            if size_threshold_ha and service_name == "cadastral":
                size_m2 = size_threshold_ha * 10000  # Convert ha to m²
                area_attr = service_config.get('area_attribute', 'kadastraleGrootteWaarde')
                params['cql_filter'] = f"{area_attr} >= {size_m2}"
            
            response = requests.get(service_config['url'], params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            # Process features to add centroid and convert geometry
            processed_features = []
            for feature in features:
                processed = self._process_feature(feature, service_config['coordinate_system'])
                if processed:
                    processed_features.append(processed)
            
            return {
                "features": processed_features,
                "service": service_name,
                "layer": layer_name,
                "count": len(processed_features)
            }
            
        except Exception as e:
            print(f"❌ Error fetching {service_name}: {e}")
            return {"features": [], "error": str(e)}
    
    def _process_feature(self, feature: Dict, srs: str) -> Optional[Dict]:
        """Process individual feature to add centroid and convert coordinates."""
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Convert geometry to WGS84 if in RD New
            if srs == "EPSG:28992" and self.transformer_to_wgs84:
                geometry = self._convert_geometry_to_wgs84(geometry)
            
            # Calculate centroid
            centroid = self._calculate_centroid(geometry)
            if not centroid:
                return None
            
            lat, lon = centroid
            
            # Create enhanced feature
            return {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry,
                "centroid": {"lat": lat, "lon": lon},
                "lat": lat,
                "lon": lon
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
    
    def perform_spatial_analysis(datasets: Dict, analysis_operations: Dict, 
                            reference_point: Optional[Dict] = None, 
                            output_requirements: Optional[Dict] = None) -> Dict:
        """
        Enhanced spatial analysis that can handle complex multi-dataset queries.
        
        Supports:
        - Area filtering (hectares, m²)
        - Distance-based filtering and proximity analysis
        - Exclusion filtering (remove overlapping features)
        - Ranking and scoring based on multiple criteria
        - Centrality analysis
        """
        
        try:
            print(f"🧮 Enhanced spatial analysis")
            print(f"   Datasets: {list(datasets.keys())}")
            print(f"   Operations: {list(analysis_operations.keys())}")
            
            # Step 1: Parse and prepare datasets
            processed_datasets = {}
            for name, dataset in datasets.items():
                if isinstance(dataset, dict) and 'features' in dataset:
                    processed_datasets[name] = _prepare_features_for_analysis(dataset['features'])
                    print(f"   Prepared {len(processed_datasets[name])} features from {name}")
            
            if not processed_datasets:
                return {"error": "No valid datasets to analyze", "success": False}
            
            # Step 2: Identify primary dataset
            primary_dataset_name = _identify_primary_dataset(analysis_operations, processed_datasets)
            primary_features = processed_datasets[primary_dataset_name]
            print(f"   Primary dataset: {primary_dataset_name} ({len(primary_features)} features)")
            
            # Step 3: Apply area filtering if specified
            if 'area_filter' in analysis_operations:
                primary_features = _apply_area_filter(primary_features, analysis_operations['area_filter'])
                print(f"   After area filtering: {len(primary_features)} features")
            
            # Step 4: Apply distance filtering if specified
            if 'distance_filter' in analysis_operations and reference_point:
                primary_features = _apply_distance_filter(
                    primary_features, analysis_operations['distance_filter'], reference_point
                )
                print(f"   After distance filtering: {len(primary_features)} features")
            
            # Step 5: Apply exclusion filtering (remove features overlapping with exclusion datasets)
            if 'exclusion_filter' in analysis_operations:
                exclusion_config = analysis_operations['exclusion_filter']
                exclusion_datasets = {
                    name: features for name, features in processed_datasets.items() 
                    if name in exclusion_config.get('exclude_datasets', [])
                }
                
                if exclusion_datasets:
                    primary_features = _apply_exclusion_filter(
                        primary_features, exclusion_datasets, exclusion_config
                    )
                    print(f"   After exclusion filtering: {len(primary_features)} features")
            
            # Step 6: Calculate proximity scores to target datasets
            if 'proximity_analysis' in analysis_operations:
                proximity_config = analysis_operations['proximity_analysis']
                target_datasets = {
                    name: features for name, features in processed_datasets.items()
                    if name in proximity_config.get('target_datasets', [])
                }
                
                primary_features = _calculate_proximity_scores(
                    primary_features, target_datasets, proximity_config
                )
                print(f"   Added proximity scores for {len(target_datasets)} target datasets")
            
            # Step 7: Calculate centrality scores if specified
            if 'centrality_analysis' in analysis_operations and reference_point:
                primary_features = _calculate_centrality_scores(
                    primary_features, reference_point, analysis_operations['centrality_analysis']
                )
                print("   Added centrality scores")
            
            # Step 8: Calculate composite scores and ranking
            if 'ranking' in analysis_operations:
                primary_features = _calculate_composite_scores_and_rank(
                    primary_features, analysis_operations['ranking']
                )
                print("   Applied ranking and scoring")
            
            # Step 9: Apply result limits and sorting
            max_results = output_requirements.get('max_results', 100) if output_requirements else 100
            if len(primary_features) > max_results:
                # Sort by composite score (highest first) and limit results
                primary_features = sorted(
                    primary_features, 
                    key=lambda x: x.get('composite_score', 0), 
                    reverse=True
                )[:max_results]
                print(f"   Limited to top {max_results} results")
            
            # Step 10: Format results for map display
            formatted_features = _format_features_for_map(primary_features)
            
            return {
                "analysis_results": {
                    "features": formatted_features,
                    "total_processed": len(primary_features),
                    "datasets_used": list(processed_datasets.keys()),
                    "operations_applied": list(analysis_operations.keys())
                },
                "formatted_output": {
                    "features": formatted_features,
                    "count": len(formatted_features),
                    "analysis_summary": {
                        "primary_dataset": primary_dataset_name,
                        "operations_performed": list(analysis_operations.keys()),
                        "total_features": len(formatted_features)
                    }
                },
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Enhanced spatial analysis failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "error": error_msg,
                "success": False
            }


    def _prepare_features_for_analysis(features):
        """Prepare features with standardized fields for analysis."""
        prepared = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
                
            # Ensure required fields exist
            prep_feature = {
                **feature,
                'analysis_metadata': {
                    'area_m2': _extract_area_m2(feature),
                    'area_ha': _extract_area_m2(feature) / 10000 if _extract_area_m2(feature) else 0,
                    'centroid': _extract_centroid(feature),
                    'original_properties': feature.get('properties', {})
                }
            }
            prepared.append(prep_feature)
        
        return prepared


    def _extract_area_m2(feature):
        """Extract area in square meters from various possible field names."""
        properties = feature.get('properties', {})
        
        # Try common area field names
        area_fields = [
            'kadastraleGrootteWaarde', 'oppervlakte', 'oppervlakte_max', 
            'oppervlakte_min', 'area_m2', 'area', 'superficie'
        ]
        
        for field in area_fields:
            if field in properties and properties[field]:
                try:
                    return float(properties[field])
                except (ValueError, TypeError):
                    continue
        
        return 0


    def _extract_centroid(feature):
        """Extract centroid coordinates from feature."""
        if 'centroid' in feature:
            return feature['centroid']
        elif 'lat' in feature and 'lon' in feature:
            return {'lat': feature['lat'], 'lon': feature['lon']}
        else:
            # Calculate from geometry if available
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'Point':
                coords = geometry.get('coordinates', [])
                return {'lat': coords[1], 'lon': coords[0]} if len(coords) >= 2 else None
            elif geometry.get('type') == 'Polygon':
                coords = geometry.get('coordinates', [[]])
                if coords and coords[0]:
                    # Calculate centroid of polygon
                    ring = coords[0]
                    avg_lon = sum(c[0] for c in ring) / len(ring)
                    avg_lat = sum(c[1] for c in ring) / len(ring)
                    return {'lat': avg_lat, 'lon': avg_lon}
        
        return None


    def _identify_primary_dataset(analysis_operations, datasets):
        """Identify which dataset is the primary one to analyze."""
        if 'primary_dataset' in analysis_operations:
            return analysis_operations['primary_dataset']
        
        # Heuristic: largest dataset is usually primary
        return max(datasets.keys(), key=lambda k: len(datasets[k]))


    def _apply_area_filter(features, area_config):
        """Filter features by area (supports hectares and m²)."""
        filtered = []
        
        min_area_m2 = area_config.get('min_area_m2', 0)
        max_area_m2 = area_config.get('max_area_m2', float('inf'))
        min_area_ha = area_config.get('min_area_ha', 0)
        max_area_ha = area_config.get('max_area_ha', float('inf'))
        
        # Convert hectares to m² if specified
        if min_area_ha > 0:
            min_area_m2 = max(min_area_m2, min_area_ha * 10000)
        if max_area_ha < float('inf'):
            max_area_m2 = min(max_area_m2, max_area_ha * 10000)
        
        for feature in features:
            area_m2 = feature['analysis_metadata']['area_m2']
            if min_area_m2 <= area_m2 <= max_area_m2:
                filtered.append(feature)
        
        return filtered


    def _apply_distance_filter(features, distance_config, reference_point):
        """Filter features by distance from reference point."""
        filtered = []
        
        max_distance_km = distance_config.get('max_distance_km', float('inf'))
        min_distance_km = distance_config.get('min_distance_km', 0)
        
        ref_lat = reference_point.get('lat') or reference_point.get('center', [0, 0])[0]
        ref_lon = reference_point.get('lon') or reference_point.get('center', [0, 0])[1]
        
        for feature in features:
            centroid = feature['analysis_metadata']['centroid']
            if not centroid:
                continue
                
            distance_km = _calculate_distance(
                ref_lat, ref_lon, centroid['lat'], centroid['lon']
            )
            
            if min_distance_km <= distance_km <= max_distance_km:
                feature['analysis_metadata']['distance_from_reference'] = distance_km
                filtered.append(feature)
        
        return filtered


    def _apply_exclusion_filter(primary_features, exclusion_datasets, exclusion_config):
        """Remove primary features that overlap with exclusion dataset features."""
        buffer_km = exclusion_config.get('buffer_km', 0.1)  # Default 100m buffer
        
        # Collect all exclusion features
        all_exclusion_features = []
        for dataset_name, features in exclusion_datasets.items():
            all_exclusion_features.extend(features)
        
        filtered = []
        for primary_feature in primary_features:
            primary_centroid = primary_feature['analysis_metadata']['centroid']
            if not primary_centroid:
                continue
            
            # Check if primary feature is too close to any exclusion feature
            is_excluded = False
            min_exclusion_distance = float('inf')
            
            for exclusion_feature in all_exclusion_features:
                exclusion_centroid = exclusion_feature['analysis_metadata']['centroid']
                if not exclusion_centroid:
                    continue
                
                distance_km = _calculate_distance(
                    primary_centroid['lat'], primary_centroid['lon'],
                    exclusion_centroid['lat'], exclusion_centroid['lon']
                )
                
                min_exclusion_distance = min(min_exclusion_distance, distance_km)
                
                if distance_km <= buffer_km:
                    is_excluded = True
                    break
            
            if not is_excluded:
                primary_feature['analysis_metadata']['min_exclusion_distance'] = min_exclusion_distance
                filtered.append(primary_feature)
        
        return filtered


    def _calculate_proximity_scores(primary_features, target_datasets, proximity_config):
        """Calculate proximity scores to target datasets."""
        for primary_feature in primary_features:
            primary_centroid = primary_feature['analysis_metadata']['centroid']
            if not primary_centroid:
                continue
            
            proximity_scores = {}
            nearest_features = {}
            
            for dataset_name, target_features in target_datasets.items():
                min_distance = float('inf')
                nearest_feature = None
                
                for target_feature in target_features:
                    target_centroid = target_feature['analysis_metadata']['centroid']
                    if not target_centroid:
                        continue
                    
                    distance_km = _calculate_distance(
                        primary_centroid['lat'], primary_centroid['lon'],
                        target_centroid['lat'], target_centroid['lon']
                    )
                    
                    if distance_km < min_distance:
                        min_distance = distance_km
                        nearest_feature = target_feature
                
                proximity_scores[dataset_name] = min_distance
                nearest_features[dataset_name] = {
                    'distance_km': min_distance,
                    'feature': nearest_feature
                }
            
            primary_feature['analysis_metadata']['proximity_scores'] = proximity_scores
            primary_feature['analysis_metadata']['nearest_features'] = nearest_features
        
        return primary_features


    def _calculate_centrality_scores(features, reference_point, centrality_config):
        """Calculate centrality scores based on distance from reference point."""
        ref_lat = reference_point.get('lat') or reference_point.get('center', [0, 0])[0]
        ref_lon = reference_point.get('lon') or reference_point.get('center', [0, 0])[1]
        
        # Calculate distances and find max for normalization
        distances = []
        for feature in features:
            centroid = feature['analysis_metadata']['centroid']
            if centroid:
                distance = _calculate_distance(ref_lat, ref_lon, centroid['lat'], centroid['lon'])
                feature['analysis_metadata']['distance_from_center'] = distance
                distances.append(distance)
        
        if not distances:
            return features
        
        max_distance = max(distances)
        
        # Calculate centrality score (closer = higher score)
        for feature in features:
            distance = feature['analysis_metadata'].get('distance_from_center', max_distance)
            # Centrality score: 1.0 for closest, approaching 0 for farthest
            centrality_score = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0
            feature['analysis_metadata']['centrality_score'] = centrality_score
        
        return features


    def _calculate_composite_scores_and_rank(features, ranking_config):
        """Calculate composite scores based on multiple criteria and rank features."""
        weights = ranking_config.get('weights', {
            'area': 0.3,
            'centrality': 0.4,
            'proximity': 0.3
        })
        
        # Normalize area scores
        areas = [f['analysis_metadata']['area_ha'] for f in features]
        max_area = max(areas) if areas else 1
        
        for feature in features:
            metadata = feature['analysis_metadata']
            score_components = {}
            
            # Area score (normalized)
            area_score = metadata['area_ha'] / max_area if max_area > 0 else 0
            score_components['area'] = area_score
            
            # Centrality score (already normalized)
            centrality_score = metadata.get('centrality_score', 0)
            score_components['centrality'] = centrality_score
            
            # Proximity score (closer to target features = higher score)
            proximity_scores = metadata.get('proximity_scores', {})
            if proximity_scores:
                # Use inverse of minimum distance to any target
                min_target_distance = min(proximity_scores.values())
                # Convert to score: closer = higher score
                proximity_score = 1.0 / (1.0 + min_target_distance)
            else:
                proximity_score = 0
            score_components['proximity'] = proximity_score
            
            # Calculate weighted composite score
            composite_score = sum(
                score_components.get(criterion, 0) * weight
                for criterion, weight in weights.items()
            )
            
            feature['analysis_metadata']['score_components'] = score_components
            feature['composite_score'] = composite_score
        
        # Rank features by composite score
        features.sort(key=lambda x: x['composite_score'], reverse=True)
        for i, feature in enumerate(features):
            feature['rank'] = i + 1
        
        return features


    def _format_features_for_map(features):
        """Format features for map display with enhanced metadata."""
        formatted = []
        
        for feature in features:
            metadata = feature['analysis_metadata']
            
            # Create descriptive name
            rank = feature.get('rank', 0)
            area_ha = metadata['area_ha']
            name = f"#{rank} - {area_ha:.1f}ha" if rank > 0 else f"{area_ha:.1f}ha"
            
            # Create description with analysis results
            desc_parts = []
            if 'composite_score' in feature:
                desc_parts.append(f"Score: {feature['composite_score']:.2f}")
            if 'distance_from_center' in metadata:
                desc_parts.append(f"Distance: {metadata['distance_from_center']:.1f}km")
            if metadata.get('proximity_scores'):
                for dataset, distance in metadata['proximity_scores'].items():
                    desc_parts.append(f"{dataset}: {distance:.1f}km")
            
            description = " | ".join(desc_parts) if desc_parts else "Analyzed parcel"
            
            # Create enhanced feature for frontend
            formatted_feature = {
                "type": "Feature",
                "name": name,
                "lat": metadata['centroid']['lat'] if metadata['centroid'] else feature.get('lat', 0),
                "lon": metadata['centroid']['lon'] if metadata['centroid'] else feature.get('lon', 0),
                "description": description,
                "geometry": feature.get('geometry', {}),
                "properties": {
                    **feature.get('properties', {}),
                    'area_m2': metadata['area_m2'],
                    'area_ha': metadata['area_ha'],
                    'composite_score': feature.get('composite_score', 0),
                    'rank': feature.get('rank', 0),
                    'analysis_metadata': metadata
                }
            }
            
            formatted.append(formatted_feature)
        
        return formatted


    def _calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula."""
        try:
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
            
            return R * c
        except Exception:
            return 999.0
    
    def _calculate_basic_score(self, feature: Dict, query: str) -> float:
        """Calculate basic score for single-layer analysis."""
        score = 100.0
        
        # Penalize distance from center
        distance = feature.get('distance_from_center', 0)
        score -= distance * 5  # 5 points per km
        
        # Bonus for larger areas if relevant
        if 'area' in query.lower() or 'size' in query.lower():
            area_m2 = feature.get('properties', {}).get('kadastraleGrootteWaarde', 0)
            if area_m2 > 0:
                area_ha = area_m2 / 10000
                score += min(area_ha * 2, 50)  # Max 50 bonus points for size
        
        return max(score, 0)
    
    def _calculate_multi_layer_score(self, feature: Dict, query: str) -> float:
        """Calculate comprehensive score for multi-layer analysis."""
        score = 100.0
        
        # Base score adjustments
        distance_from_center = feature.get('distance_from_center', 0)
        score -= distance_from_center * 3  # 3 points per km from center
        
        # Size bonus for parcels
        properties = feature.get('properties', {})
        area_m2 = properties.get('kadastraleGrootteWaarde', 0)
        if area_m2 > 0:
            area_ha = area_m2 / 10000
            score += min(area_ha * 1.5, 40)  # Size bonus
        
        # Proximity scores to secondary features
        proximity_scores = feature.get('proximity_scores', {})
        
        for service, distance in proximity_scores.items():
            if distance < 1.0:  # Very close (< 1km)
                score += 30
            elif distance < 2.0:  # Close (< 2km)
                score += 20
            elif distance < 5.0:  # Moderate (< 5km)
                score += 10
            else:  # Far (> 5km)
                score -= distance * 2
        
        # Special scoring based on query intent
        if 'suitable' in query.lower() and 'nature' in query.lower():
            # Bonus for being close to nature areas
            natura_distance = proximity_scores.get('natura2000', float('inf'))
            if natura_distance < 0.5:
                score += 25  # Very close to Natura 2000
            elif natura_distance < 2.0:
                score += 15  # Reasonably close
        
        if 'farming' in query.lower():
            # Bonus for medium-sized parcels (good for farming)
            if 5 <= area_ha <= 50:
                score += 15
        
        return max(score, 0)
    
    def _rank_and_filter_results(self, results: List[Dict], max_results: int, analysis_type: str, query: str) -> List[Dict]:
        """Rank and filter results based on analysis scores."""
        
        # Sort by analysis score (highest first)
        sorted_results = sorted(results, key=lambda x: x.get('analysis_score', 0), reverse=True)
        
        # Apply additional ranking based on query keywords
        if 'rank' in query.lower():
            if 'size' in query.lower():
                # Secondary sort by size
                sorted_results = sorted(sorted_results, key=lambda x: (
                    x.get('analysis_score', 0),
                    x.get('properties', {}).get('kadastraleGrootteWaarde', 0)
                ), reverse=True)
            
            if 'proximity' in query.lower() or 'distance' in query.lower():
                # Secondary sort by proximity
                sorted_results = sorted(sorted_results, key=lambda x: (
                    x.get('analysis_score', 0),
                    -min(x.get('proximity_scores', {}).values(), default=999)
                ), reverse=True)
        
        return sorted_results[:max_results]
    
    def _format_multi_layer_response(self, results: List[Dict], datasets: Dict, pattern: Dict, query: str, center_lat: float, center_lon: float) -> Dict:
        """Format the final response with analysis results."""
        
        if not results:
            return {
                "text_description": f"No features found matching the criteria: '{query}'",
                "geojson_data": [],
                "analysis_summary": {
                    "total_results": 0,
                    "datasets_searched": list(datasets.keys()),
                    "search_center": [center_lat, center_lon]
                }
            }
        
        # Create enhanced features for map display
        enhanced_features = []
        
        for i, result in enumerate(results):
            # Create name based on ranking and properties
            rank = i + 1
            properties = result.get('properties', {})
            area_m2 = properties.get('kadastraleGrootteWaarde', 0)
            area_ha = area_m2 / 10000 if area_m2 > 0 else 0
            
            name = f"Rank #{rank}"
            if area_ha > 0:
                name += f" ({area_ha:.1f} ha)"
            
            # Create detailed description
            desc_parts = [f"Score: {result.get('analysis_score', 0):.1f}"]
            
            if area_ha > 0:
                desc_parts.append(f"Area: {area_ha:.1f} ha")
            
            if result.get('distance_from_center'):
                desc_parts.append(f"Distance: {result['distance_from_center']:.2f}km")
            
            # Add proximity information
            nearest_features = result.get('nearest_features', {})
            for service, info in nearest_features.items():
                desc_parts.append(f"{service.title()}: {info['distance_km']:.2f}km to {info['name']}")
            
            description = " | ".join(desc_parts)
            
            enhanced_feature = {
                "type": "Feature",
                "name": name,
                "lat": result['lat'],
                "lon": result['lon'],
                "description": description,
                "geometry": result['geometry'],
                "properties": {
                    **properties,
                    "analysis_score": result.get('analysis_score', 0),
                    "rank": rank,
                    "area_ha": area_ha,
                    "distance_from_center": result.get('distance_from_center', 0),
                    "proximity_info": nearest_features
                }
            }
            
            enhanced_features.append(enhanced_feature)
        
        # Create summary statistics
        analysis_summary = {
            "total_results": len(results),
            "datasets_searched": list(datasets.keys()),
            "search_center": [center_lat, center_lon],
            "top_score": results[0].get('analysis_score', 0) if results else 0,
            "average_score": sum(r.get('analysis_score', 0) for r in results) / len(results) if results else 0,
            "analysis_type": pattern['type']
        }
        
        # Add dataset statistics
        for service, data in datasets.items():
            analysis_summary[f"{service}_features_found"] = len(data.get('features', []))
        
        # Create descriptive text
        text_description = self._create_analysis_description(results, query, analysis_summary)
        
        return {
            "text_description": text_description,
            "geojson_data": enhanced_features,
            "analysis_summary": analysis_summary,
            "multi_layer_analysis": True
        }
    
    def _create_analysis_description(self, results: List[Dict], query: str, summary: Dict) -> str:
        """Create descriptive text for the analysis results."""
        
        if not results:
            return f"No results found for multi-layer analysis: '{query}'"
        
        desc = f"Multi-layer spatial analysis completed for: '{query}'\n\n"
        desc += f"Found {len(results)} features ranked by analysis score.\n"
        desc += f"Search included {len(summary['datasets_searched'])} PDOK services: {', '.join(summary['datasets_searched'])}.\n\n"
        
        # Top results summary
        top_3 = results[:3]
        desc += "Top results:\n"
        
        for i, result in enumerate(top_3):
            rank = i + 1
            score = result.get('analysis_score', 0)
            area_m2 = result.get('properties', {}).get('kadastraleGrootteWaarde', 0)
            area_ha = area_m2 / 10000 if area_m2 > 0 else 0
            
            desc += f"  #{rank}: Score {score:.1f}"
            if area_ha > 0:
                desc += f", {area_ha:.1f} ha"
            
            # Add proximity info
            nearest = result.get('nearest_features', {})
            if nearest:
                distances = [f"{k}: {v['distance_km']:.1f}km" for k, v in nearest.items()]
                desc += f", {', '.join(distances)}"
            
            desc += "\n"
        
        desc += f"\nAll results have been ranked and scored based on size, location, and proximity to relevant features."
        
        return desc


class EnhancedQueryCoordinatorTool(Tool):
    """
    Coordinator tool that analyzes complex queries and orchestrates multi-step workflows.
    This tool determines when to use single vs multi-layer analysis.
    """
    
    name = "coordinate_complex_query"
    description = """Analyze complex spatial queries and coordinate the appropriate analysis approach.

This tool determines:
- Whether a query requires single-layer or multi-layer analysis
- Which PDOK services and layers are needed
- What spatial analysis operations should be performed
- How to structure the workflow for optimal results

Use this for complex queries involving multiple criteria, ranking, or spatial relationships."""
    
    inputs = {
        "user_query": {
            "type": "string",
            "description": "The user's complete query"
        },
        "context_info": {
            "type": "object",
            "description": "Additional context like map center, zoom, current features",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, user_query: str, context_info: Optional[Dict] = None) -> Dict:
        """Analyze query and determine the best approach."""
        
        try:
            print(f"🎯 Coordinating complex query: {user_query}")
            
            # Analyze query complexity
            analysis = self._analyze_query_complexity(user_query)
            print(f"📊 Query complexity: {analysis['complexity_level']}")
            
            # Determine approach
            approach = self._determine_approach(analysis, context_info)
            print(f"🛣️ Recommended approach: {approach['method']}")
            
            # Create workflow plan
            workflow = self._create_workflow_plan(analysis, approach, user_query)
            
            return {
                "query_analysis": analysis,
                "recommended_approach": approach,
                "workflow_plan": workflow,
                "estimated_steps": len(workflow.get('steps', [])),
                "requires_multi_layer": approach['method'] == 'multi_layer'
            }
            
        except Exception as e:
            return {"error": f"Query coordination failed: {str(e)}"}
    
    def _analyze_query_complexity(self, query: str) -> Dict:
        """Analyze the complexity and requirements of the query."""
        
        query_lower = query.lower()
        
        # Detect entities and operations
        entities = []
        operations = []
        filters = []
        spatial_relations = []
        
        # Entity detection
        if any(word in query_lower for word in ['parcel', 'kadaster', 'land']):
            entities.append('parcels')
        if any(word in query_lower for word in ['building', 'roof', 'pand']):
            entities.append('buildings')
        if any(word in query_lower for word in ['natura', 'nature', 'protected']):
            entities.append('natura2000')
        if any(word in query_lower for word in ['wetland', 'water', 'ramsar']):
            entities.append('wetlands')
        if any(word in query_lower for word in ['address', 'street']):
            entities.append('addresses')
        
        # Operation detection
        if any(word in query_lower for word in ['rank', 'order', 'sort', 'top']):
            operations.append('ranking')
        if any(word in query_lower for word in ['score', 'suitable', 'best']):
            operations.append('scoring')
        if any(word in query_lower for word in ['near', 'close', 'proximity', 'distance']):
            operations.append('proximity_analysis')
        if any(word in query_lower for word in ['within', 'around', 'radius']):
            operations.append('spatial_buffer')
        
        # Filter detection
        if any(word in query_lower for word in ['>', 'larger', 'bigger', 'above']):
            filters.append('size_filter')
        if any(word in query_lower for word in ['ha', 'hectare', 'km²', 'm²']):
            filters.append('area_filter')
        
        # Spatial relation detection
        if any(phrase in query_lower for phrase in ['close to', 'near to', 'next to']):
            spatial_relations.append('proximity')
        if any(phrase in query_lower for phrase in ['within', 'inside']):
            spatial_relations.append('containment')
        if any(phrase in query_lower for phrase in ['between', 'among']):
            spatial_relations.append('between')
        
        # Determine complexity level
        complexity_score = len(entities) + len(operations) + len(spatial_relations)
        
        if complexity_score <= 2:
            complexity_level = "simple"
        elif complexity_score <= 4:
            complexity_level = "moderate"
        else:
            complexity_level = "complex"
        
        return {
            "entities": entities,
            "operations": operations,
            "filters": filters,
            "spatial_relations": spatial_relations,
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "requires_multi_layer": len(entities) > 1 or len(spatial_relations) > 0
        }
    
    def _determine_approach(self, analysis: Dict, context_info: Optional[Dict]) -> Dict:
        """Determine the best approach based on analysis."""
        
        entities = analysis['entities']
        operations = analysis['operations']
        
        # Multi-layer analysis needed if:
        # 1. Multiple entities
        # 2. Spatial relations between different entity types
        # 3. Ranking/scoring operations involving proximity
        
        if len(entities) > 1:
            return {
                "method": "multi_layer",
                "reason": f"Query involves multiple entity types: {', '.join(entities)}",
                "primary_entity": entities[0] if entities else "parcels",
                "secondary_entities": entities[1:] if len(entities) > 1 else [],
                "tools_needed": ["analyze_multiple_spatial_layers"]
            }
        
        elif 'proximity_analysis' in operations and 'ranking' in operations:
            return {
                "method": "multi_layer", 
                "reason": "Query requires proximity analysis with ranking",
                "primary_entity": entities[0] if entities else "parcels",
                "secondary_entities": ["natura2000"],  # Common secondary
                "tools_needed": ["analyze_multiple_spatial_layers"]
            }
        
        elif 'scoring' in operations:
            return {
                "method": "multi_layer",
                "reason": "Query requires scoring which may involve multiple factors",
                "primary_entity": entities[0] if entities else "parcels", 
                "secondary_entities": ["natura2000"],
                "tools_needed": ["analyze_multiple_spatial_layers"]
            }
        
        else:
            return {
                "method": "single_layer",
                "reason": "Query can be handled with single PDOK service",
                "primary_entity": entities[0] if entities else "parcels",
                "tools_needed": ["discover_pdok_services", "search_location_coordinates", "request_pdok_data"]
            }
    
    def _create_workflow_plan(self, analysis: Dict, approach: Dict, query: str) -> Dict:
        """Create a detailed workflow plan."""
        
        workflow = {
            "method": approach["method"],
            "steps": []
        }
        
        if approach["method"] == "multi_layer":
            workflow["steps"] = [
                {
                    "step": 1,
                    "action": "Extract location and parameters from query",
                    "details": "Parse location names, size thresholds, radius, etc."
                },
                {
                    "step": 2, 
                    "action": "Use analyze_multiple_spatial_layers tool",
                    "details": f"Perform multi-layer analysis for entities: {', '.join(analysis['entities'])}"
                },
                {
                    "step": 3,
                    "action": "Format results for map display",
                    "details": "Create ranked, scored results with proper descriptions"
                }
            ]
        else:
            workflow["steps"] = [
                {
                    "step": 1,
                    "action": "Discover PDOK services and attributes",
                    "details": "Use discover_pdok_services with get_attributes=True"
                },
                {
                    "step": 2,
                    "action": "Find location coordinates if needed",
                    "details": "Use search_location_coordinates for location mentions"
                },
                {
                    "step": 3,
                    "action": "Make PDOK data request",
                    "details": "Use request_pdok_data with proper filters"
                },
                {
                    "step": 4,
                    "action": "Format results",
                    "details": "Create JSON response with text_description and geojson_data"
                }
            ]
        
        return workflow




def create_enhanced_system_prompt_extension():
    """Create an enhanced system prompt extension for multi-layer analysis."""
    
    return """
    
## ENHANCED MULTI-LAYER ANALYSIS CAPABILITIES

You now have access to enhanced tools for complex spatial analysis:

### 🎯 Query Coordination Tool
```python
# Use this to analyze complex queries first
coordination = coordinate_complex_query(user_query="Show me parcels >5ha near Natura 2000 areas around Amsterdam")

if coordination['requires_multi_layer']:
    # Use multi-layer analysis
    result = analyze_multiple_spatial_layers(
        query_description=user_query,
        center_lat=52.3676,
        center_lon=4.9041,
        search_radius_km=10,
        size_threshold_ha=5
    )
else:
    # Use standard single-layer approach
    # ... existing workflow
```

### 🔍 Multi-Layer Spatial Analysis Tool
```python
# For complex queries involving multiple PDOK services
result = analyze_multiple_spatial_layers(
    query_description="Find parcels >7ha near Natura 2000 areas and rank by proximity",
    center_lat=52.3676,  # or extract from location
    center_lon=4.9041,
    search_radius_km=15,
    size_threshold_ha=7,
    max_results=50
)
```

### 🧠 ENHANCED INTELLIGENCE WORKFLOW

For complex multi-layer queries, follow this pattern:

1. **Analyze Query Complexity**:
   ```python
   coordination = coordinate_complex_query(user_query)
   requires_multi_layer = coordination['requires_multi_layer']
   ```

2. **Extract Parameters**:
   ```python
   # Extract size thresholds
   import re
   ha_match = re.search(r'(\d+)\s*ha', user_query, re.IGNORECASE)
   size_threshold_ha = float(ha_match.group(1)) if ha_match else None
   
   # Extract radius
   radius_match = re.search(r'(\d+)\s*km', user_query, re.IGNORECASE)
   radius_km = float(radius_match.group(1)) if radius_match else 10
   ```

3. **Use Multi-Layer Analysis**:
   ```python
   if requires_multi_layer:
       result = analyze_multiple_spatial_layers(
           query_description=user_query,
           center_lat=center_lat,
           center_lon=center_lon, 
           search_radius_km=radius_km,
           size_threshold_ha=size_threshold_ha,
           max_results=50
       )
       
       # Format response
       import json
       final_answer(json.dumps({
           "text_description": result['text_description'],
           "geojson_data": result['geojson_data']
       }))
   ```

### 📋 QUERY PATTERNS THAT REQUIRE MULTI-LAYER ANALYSIS

- **Parcels + Natura 2000**: "Show parcels >5ha near Natura 2000 areas"
- **Ranking by proximity**: "Rank parcels by distance to protected areas"
- **Multiple criteria scoring**: "Score parcels based on size and environmental proximity"
- **Environmental suitability**: "Find parcels suitable for nature-inclusive farming"
- **Solar panel suitability**: "Which roofs are most suitable for solar panels"
- **Complex spatial relationships**: "Find parcels between water and nature areas"

### ⚡ EXAMPLE ENHANCED WORKFLOW

```python
# Step 1: Analyze the query
user_query = "Show me all parcels bigger than 7 ha near [52.3702, 4.8952] and close to a Natura 2000 area"

coordination = coordinate_complex_query(user_query)
print(f"Analysis: {coordination['query_analysis']}")
print(f"Requires multi-layer: {coordination['requires_multi_layer']}")

# Step 2: Extract coordinates and parameters
center_lat, center_lon = 52.3702, 4.8952
size_threshold_ha = 7

# Step 3: Use multi-layer analysis
result = analyze_multiple_spatial_layers(
    query_description=user_query,
    center_lat=center_lat,
    center_lon=center_lon,
    search_radius_km=10,
    size_threshold_ha=size_threshold_ha,
    max_results=30
)

# Step 4: Return structured response
import json
final_answer(json.dumps({
    "text_description": result['text_description'],
    "geojson_data": result['geojson_data']
}))
```

### 🔑 KEY ADVANTAGES

- ✅ **Handles multiple PDOK services simultaneously**
- ✅ **Performs spatial proximity analysis between different layer types**  
- ✅ **Ranks and scores results based on multiple criteria**
- ✅ **Supports complex filtering (size + location + proximity)**
- ✅ **Provides detailed analysis scores and explanations**
- ✅ **Formats results properly for map display**

Always use the coordination tool first to determine the best approach for complex queries!
"""