# tools/pdok_modular_tools.py
"""
"""

import math
import re
import requests
import json
from datetime import datetime
from smolagents import Tool
from typing import Dict, List, Optional, Tuple, Union

class PDOKLocationSearchTool(Tool):
    """
    Standalone location search tool for finding Dutch locations and addresses.
    This tool ONLY finds locations and returns coordinates - it doesn't search for buildings.
    """
    
    name = "find_dutch_location"
    description = """Find coordinates and details for any Dutch location or address.
    
    This tool searches the PDOK Locatieserver to find coordinates for:
    - Specific addresses (e.g., "Leonard Springerlaan 37, Groningen")
    - Cities and towns (e.g., "Amsterdam", "Groningen")
    - Landmarks (e.g., "Amsterdam Centraal", "Groningen train station")
    - Postal codes (e.g., "1012AB")
    - Streets (e.g., "Damrak, Amsterdam")
    
    Returns precise latitude/longitude coordinates and administrative information.
    Use this tool when you need to find WHERE a location is before searching for buildings there."""
    
    inputs = {
        "location_query": {
            "type": "string", 
            "description": "Location to search for (address, city, landmark, postal code, etc.)"
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
        
    def forward(self, location_query: str) -> Dict:
        """Find Dutch location and return coordinates."""
        try:
            print(f"🔍 Searching for location: '{location_query}'")
            
            # Clean and optimize query
            clean_query = self._clean_query(location_query)
            
            # Search with multiple strategies
            result = self._search_location(clean_query)
            
            if result.get('error'):
                # Try fallback search
                fallback_result = self._fallback_search(location_query)
                if not fallback_result.get('error'):
                    result = fallback_result
            
            return result
            
        except Exception as e:
            return {"error": f"Location search failed: {str(e)}"}
    
    def _clean_query(self, query: str) -> str:
        """Clean and optimize the search query."""
        # Remove common words that don't help location search
        query = query.replace("near", "").replace("around", "").replace("close to", "")
        query = query.replace("buildings", "").replace("show me", "").replace("find", "")
        return query.strip()
    
    def _search_location(self, query: str) -> Dict:
        """Execute PDOK location search."""
        try:
            params = {
                'q': query,
                'rows': 10,
                'fl': 'weergavenaam,centroide_ll,type,score,gemeentenaam,provincienaam,straatnaam,huisnummer,postcode,woonplaatsnaam',
                'fq': 'type:(adres OR woonplaats OR gemeente OR weg OR postcode)',
                'wt': 'json'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if not docs:
                return {"error": f"No location found for '{query}'"}
            
            # Select best result
            best_doc = self._select_best_result(docs, query)
            
            # Extract coordinates
            coords = self._extract_coordinates(best_doc)
            if not coords:
                return {"error": "Could not extract coordinates from result"}
            
            lat, lon = coords
            
            # Build result
            result = {
                "name": best_doc.get('weergavenaam', query),
                "lat": lat,
                "lon": lon,
                "type": best_doc.get('type', 'unknown'),
                "municipality": best_doc.get('gemeentenaam', ''),
                "province": best_doc.get('provincienaam', ''),
                "description": self._build_description(best_doc),
                "search_query": query
            }
            
            print(f"✅ Found: {result['name']} at {lat:.6f}, {lon:.6f}")
            return result
            
        except Exception as e:
            return {"error": f"PDOK search error: {str(e)}"}
    
    def _fallback_search(self, query: str) -> Dict:
        """Fallback search with broader parameters."""
        try:
            params = {
                'q': query,
                'rows': 15,
                'fl': 'weergavenaam,centroide_ll,type,score',
                'wt': 'json'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if docs:
                best_doc = docs[0]  # Take first result
                coords = self._extract_coordinates(best_doc)
                if coords:
                    lat, lon = coords
                    return {
                        "name": best_doc.get('weergavenaam', query),
                        "lat": lat,
                        "lon": lon,
                        "type": best_doc.get('type', 'unknown'),
                        "description": f"Fallback result: {best_doc.get('weergavenaam', query)}",
                        "search_query": query
                    }
            
            return {"error": f"No location found even with fallback search for '{query}'"}
            
        except Exception as e:
            return {"error": f"Fallback search error: {str(e)}"}
    
    def _select_best_result(self, docs: List[Dict], query: str) -> Dict:
        """Select the best result from search results."""
        if not docs:
            return {}
        
        # Score results
        scored = []
        query_lower = query.lower()
        
        for doc in docs:
            score = doc.get('score', 0)
            weergavenaam = doc.get('weergavenaam', '').lower()
            
            # Boost score for better matches
            if query_lower in weergavenaam:
                score += 10
            
            # Prefer addresses
            if doc.get('type') == 'adres':
                score += 5
            
            scored.append((score, doc))
        
        # Return best scored result
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    
    def _extract_coordinates(self, doc: Dict) -> Optional[Tuple[float, float]]:
        """Extract lat/lon coordinates from PDOK result."""
        centroide = doc.get('centroide_ll')
        if not centroide:
            return None
        
        try:
            if isinstance(centroide, str):
                # Handle POINT(lon lat) format
                coords_str = centroide.replace('POINT(', '').replace(')', '')
                coords = coords_str.split()
                if len(coords) == 2:
                    lon, lat = float(coords[0]), float(coords[1])
                    return lat, lon
            elif isinstance(centroide, list) and len(centroide) == 2:
                lon, lat = float(centroide[0]), float(centroide[1])
                return lat, lon
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _build_description(self, doc: Dict) -> str:
        """Build a description from document fields."""
        parts = []
        
        if doc.get('straatnaam') and doc.get('huisnummer'):
            parts.append(f"{doc['straatnaam']} {doc['huisnummer']}")
        elif doc.get('straatnaam'):
            parts.append(doc['straatnaam'])
        
        if doc.get('woonplaatsnaam'):
            parts.append(doc['woonplaatsnaam'])
        
        if doc.get('gemeentenaam') and doc.get('gemeentenaam') != doc.get('woonplaatsnaam'):
            parts.append(doc['gemeentenaam'])
        
        if doc.get('postcode'):
            parts.append(doc['postcode'])
        
        return ", ".join(parts) if parts else doc.get('weergavenaam', 'Unknown location')


class PDOKBuildingSearchTool(Tool):
    """
    Searches for buildings in PDOK BAG database near a specific location.
    Requires coordinates as input - use find_dutch_location first to get coordinates.
    """
    
    name = "search_pdok_buildings"
    description = """Search for buildings in the Dutch BAG database near specific coordinates.
    
    This tool searches for buildings (panden) in the PDOK BAG WFS service.
    It requires precise coordinates as input - use find_dutch_location first to get coordinates.
    
    Can filter buildings by:
    - Construction year (e.g., built before 1950)
    - Building area (e.g., larger than 300m²)
    - Distance from search point
    
    Returns building data with geometry (points or polygons), construction year, area, and other properties.
    Building polygons are preserved as polygons for proper map display."""
    
    inputs = {
        "lat": {"type": "number", "description": "Latitude of search center"},
        "lon": {"type": "number", "description": "Longitude of search center"},
        "radius_km": {"type": "number", "description": "Search radius in kilometers (default: 1.0)"},
        "min_area": {"type": "number", "description": "Minimum building area in m² (optional)", "nullable": True},
        "max_year": {"type": "number", "description": "Maximum construction year (optional)", "nullable": True},
        "max_buildings": {"type": "number", "description": "Maximum number of buildings to return (default: 50)"}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.wfs_url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
        
        # Initialize coordinate transformer if available
        try:
            import pyproj
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.has_pyproj = True
        except ImportError:
            self.has_pyproj = False
            print("⚠️ PyProj not available - coordinate transformation limited")
    
    def forward(self, lat: float, lon: float, radius_km: float = 1.0, 
                min_area: Optional[float] = None, max_year: Optional[int] = None, 
                max_buildings: int = 50) -> Dict:
        """Search for buildings near coordinates."""
        try:
            print(f"🏗️ Searching for buildings near {lat:.6f}, {lon:.6f} (radius: {radius_km}km)")
            
            # Create spatial filter
            bbox = self._create_bbox(lat, lon, radius_km)
            if not bbox:
                return {"error": "Could not create spatial bounding box"}
            
            # Build WFS parameters
            params = self._build_wfs_params(bbox, min_area, max_year, max_buildings)
            
            # Execute WFS request
            response = requests.get(self.wfs_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            features = data.get('features', [])
            
            print(f"📦 PDOK returned {len(features)} raw features")
            
            if not features:
                return {
                    "text_description": f"No buildings found near {lat:.6f}, {lon:.6f} within {radius_km}km radius",
                    "geojson_data": [],
                    "search_info": {"lat": lat, "lon": lon, "radius_km": radius_km}
                }
            
            # Process features
            processed_buildings = self._process_buildings(features, lat, lon, min_area, max_year)
            
            # Create response
            description = self._create_description(processed_buildings, lat, lon, radius_km, min_area, max_year)
            
            return {
                "text_description": description,
                "geojson_data": processed_buildings,
                "search_info": {
                    "lat": lat, 
                    "lon": lon, 
                    "radius_km": radius_km,
                    "min_area": min_area,
                    "max_year": max_year,
                    "total_found": len(processed_buildings)
                }
            }
            
        except Exception as e:
            error_msg = f"Building search failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def _create_bbox(self, lat: float, lon: float, radius_km: float) -> Optional[List[float]]:
        """Create bounding box in RD New coordinates."""
        if not self.has_pyproj:
            # Fallback: approximate bbox in WGS84
            lat_offset = radius_km / 111.0  # Rough conversion
            lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
            return [lon - lon_offset, lat - lat_offset, lon + lon_offset, lat + lat_offset]
        
        try:
            # Transform center to RD New
            center_x, center_y = self.transformer_to_rd.transform(lon, lat)
            
            # Create bbox in meters
            radius_m = radius_km * 1000
            return [
                center_x - radius_m,
                center_y - radius_m,
                center_x + radius_m,
                center_y + radius_m
            ]
        except Exception as e:
            print(f"❌ Error creating bbox: {e}")
            return None
    
    def _build_wfs_params(self, bbox: List[float], min_area: Optional[float], 
                         max_year: Optional[int], max_buildings: int) -> Dict:
        """Build WFS request parameters."""
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': 'bag:pand',
            'outputFormat': 'application/json',
            'count': min(max_buildings * 3, 1000),  # Get extra for filtering
            'srsName': 'EPSG:28992' if self.has_pyproj else 'EPSG:4326'
        }
        
        # Add bbox
        if self.has_pyproj:
            params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:28992"
        else:
            params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:4326"
        
        # Add attribute filters
        cql_filters = []
        if min_area:
            cql_filters.append(f"oppervlakte_min >= {min_area}")
        if max_year:
            cql_filters.append(f"bouwjaar <= {max_year}")
        
        if cql_filters:
            params['cql_filter'] = " AND ".join(cql_filters)
            print(f"🔍 Applied filters: {params['cql_filter']}")
        
        return params
    
    def _process_buildings(self, features: List[Dict], search_lat: float, search_lon: float,
                          min_area: Optional[float], max_year: Optional[int]) -> List[Dict]:
        """Process building features and convert to display format."""
        processed = []
        
        for i, feature in enumerate(features):
            try:
                props = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                # Skip invalid features
                if not geometry or not props:
                    continue
                
                # Apply additional filters
                if not self._passes_filters(props, min_area, max_year):
                    continue
                
                # Get building centroid for distance calculation
                centroid_wgs84 = self._get_building_centroid(geometry)
                if not centroid_wgs84:
                    continue
                
                lat, lon = centroid_wgs84
                
                # Calculate distance
                distance_km = self._calculate_distance(search_lat, search_lon, lat, lon)
                
                # Convert geometry to WGS84 if needed
                display_geometry = self._convert_geometry_to_wgs84(geometry)
                
                # Create building feature
                building = {
                    "name": self._create_building_name(props, i),
                    "lat": lat,
                    "lon": lon,
                    "description": self._create_building_description(props, distance_km),
                    "geometry": display_geometry,  # Preserve original geometry type
                    "properties": {
                        **props,
                        "distance_km": distance_km,
                        "centroid_lat": lat,
                        "centroid_lon": lon
                    }
                }
                
                processed.append(building)
                
            except Exception as e:
                print(f"❌ Error processing building {i}: {e}")
                continue
        
        # Sort by distance
        processed.sort(key=lambda x: x['properties']['distance_km'])
        
        print(f"✅ Processed {len(processed)} buildings")
        return processed
    
    def _passes_filters(self, props: Dict, min_area: Optional[float], max_year: Optional[int]) -> bool:
        """Check if building passes additional filters."""
        # Area check
        if min_area:
            area = props.get('oppervlakte_min') or props.get('oppervlakte_max', 0)
            if area < min_area:
                return False
        
        # Year check
        if max_year:
            year = props.get('bouwjaar')
            if year and year > max_year:
                return False
        
        return True
    
    def _get_building_centroid(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """Get building centroid in WGS84."""
        try:
            geom_type = geometry.get('type')
            coords = geometry.get('coordinates')
            
            if not coords:
                return None
            
            if geom_type == 'Point':
                if self.has_pyproj:
                    # Convert from RD to WGS84
                    wgs84 = self.transformer_to_wgs84.transform(coords[0], coords[1])
                    return wgs84[1], wgs84[0]  # lat, lon
                else:
                    return coords[1], coords[0]  # lat, lon
                    
            elif geom_type == 'Polygon':
                # Calculate centroid of exterior ring
                exterior = coords[0]
                if exterior:
                    avg_x = sum(c[0] for c in exterior) / len(exterior)
                    avg_y = sum(c[1] for c in exterior) / len(exterior)
                    
                    if self.has_pyproj:
                        wgs84 = self.transformer_to_wgs84.transform(avg_x, avg_y)
                        return wgs84[1], wgs84[0]  # lat, lon
                    else:
                        return avg_y, avg_x  # lat, lon
            
            return None
            
        except Exception as e:
            print(f"❌ Error calculating centroid: {e}")
            return None
    
    def _convert_geometry_to_wgs84(self, geometry: Dict) -> Dict:
        """Convert geometry from RD New to WGS84 while preserving type."""
        if not self.has_pyproj:
            return geometry  # Return as-is if no transformation available
        
        try:
            geom_type = geometry.get('type')
            coords = geometry.get('coordinates')
            
            if geom_type == 'Point':
                wgs84 = self.transformer_to_wgs84.transform(coords[0], coords[1])
                return {'type': 'Point', 'coordinates': [wgs84[0], wgs84[1]]}
                
            elif geom_type == 'Polygon':
                wgs84_coords = []
                for ring in coords:
                    wgs84_ring = []
                    for coord in ring:
                        wgs84 = self.transformer_to_wgs84.transform(coord[0], coord[1])
                        wgs84_ring.append([wgs84[0], wgs84[1]])
                    wgs84_coords.append(wgs84_ring)
                return {'type': 'Polygon', 'coordinates': wgs84_coords}
            
            # For other geometry types, return as-is
            return geometry
            
        except Exception as e:
            print(f"❌ Error converting geometry: {e}")
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
    
    def _create_building_name(self, props: Dict, index: int) -> str:
        """Create a name for the building."""
        building_id = props.get('identificatie', f'Building_{index+1}')
        year = props.get('bouwjaar')
        
        # Shorten ID for display
        if len(building_id) > 10:
            short_id = building_id[-6:]
        else:
            short_id = building_id
        
        if year:
            return f"Building {short_id} ({year})"
        else:
            return f"Building {short_id}"
    
    def _create_building_description(self, props: Dict, distance_km: float) -> str:
        """Create description for building."""
        parts = [f"Distance: {distance_km:.3f}km"]
        
        if props.get('bouwjaar'):
            year = props['bouwjaar']
            age = 2024 - year
            parts.append(f"Built: {year} ({age} years old)")
        
        area = props.get('oppervlakte_min') or props.get('oppervlakte_max')
        if area:
            parts.append(f"Area: {area:,.0f}m²")
        
        if props.get('status'):
            parts.append(f"Status: {props['status']}")
        
        return " | ".join(parts)
    
    def _create_description(self, buildings: List[Dict], lat: float, lon: float, 
                           radius_km: float, min_area: Optional[float], max_year: Optional[int]) -> str:
        """Create text description of search results."""
        if not buildings:
            return f"No buildings found near {lat:.6f}°N, {lon:.6f}°E within {radius_km}km radius"
        
        description_parts = [
            f"## Building Search Results",
            f"Found **{len(buildings)} buildings** near {lat:.6f}°N, {lon:.6f}°E",
            f"Search radius: {radius_km}km"
        ]
        
        if min_area:
            description_parts.append(f"Minimum area: {min_area}m²")
        if max_year:
            description_parts.append(f"Built before: {max_year}")
        
        # Add sample buildings
        sample_count = min(5, len(buildings))
        description_parts.append(f"\n**Sample buildings found:**")
        
        for building in buildings[:sample_count]:
            description_parts.append(f"• **{building['name']}** - {building['description']}")
        
        if len(buildings) > sample_count:
            description_parts.append(f"... and {len(buildings) - sample_count} more buildings")
        
        description_parts.append(f"\nAll buildings are displayed on the map with their actual geometry (polygons preserved as polygons).")
        
        return "\n".join(description_parts)


class PDOKServiceDiscoveryTool(Tool):
    """
    Discovers available PDOK WFS services and their capabilities.
    """
    
    name = "discover_pdok_services"
    description = """Discover available PDOK WFS services and their layers.
    
    This tool checks what PDOK services are available and provides information about:
    - Available WFS services and their URLs
    - Layer names and descriptions
    - Service capabilities and status
    - Usage examples
    
    Use this when you need to know what PDOK services are available or how to access specific data types."""
    
    inputs = {
        "service_type": {
            "type": "string", 
            "description": "Type of service to discover ('bag', 'bgt', 'brt', 'all')"
        }
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, service_type: str = "all") -> Dict:
        """Discover PDOK services."""
        try:
            services = {
                "bag": {
                    "name": "BAG - Buildings and Addresses",
                    "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                    "description": "Dutch Buildings and Addresses Database",
                    "layers": {
                        "bag:pand": "Buildings (polygons)",
                        "bag:verblijfsobject": "Residential objects", 
                        "bag:nummeraanduiding": "Address numbers",
                        "bag:openbare_ruimte": "Public spaces"
                    }
                },
                "bgt": {
                    "name": "BGT - Large Scale Topography",
                    "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0",
                    "description": "Large scale topographic data",
                    "layers": {
                        "bgt:gebouw_vlak": "Building surfaces",
                        "bgt:wegdeel_vlak": "Road surfaces",
                        "bgt:waterdeel_vlak": "Water surfaces"
                    }
                }
            }
            
            if service_type == "all":
                return {"services": services, "total": len(services)}
            elif service_type in services:
                return {"services": {service_type: services[service_type]}, "total": 1}
            else:
                return {"error": f"Unknown service type: {service_type}"}
                
        except Exception as e:
            return {"error": f"Service discovery failed: {str(e)}"}