"""
PDOK Buildings WFS Client with Polygon Geometry Support

This client retrieves building data from the Dutch PDOK (Publieke Dienstverlening Op de Kaart) 
WFS service, including full polygon geometry data and coordinate transformations.

Required dependencies:
    pip install requests shapely pyproj

Features:
- Retrieve building polygons with geometry data
- Calculate area, perimeter, centroid, and bounds
- Convert between RD New (EPSG:28992) and WGS84 (EPSG:4326)
- Filter by location, construction year, postal code, etc.
- Export geometry data in multiple formats
"""

import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Tuple, Union
import json
from shapely.geometry import shape, Polygon, Point
from shapely.ops import transform
import pyproj

class PDOKBuildingsClient:
    """
    Client for requesting building data from PDOK WFS service
    """
    
    def __init__(self):
        self.base_url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
        self.typename = "bag:pand"
        self.srs = "EPSG:28992"  # Dutch coordinate system
        self.version = "2.0.0"
        
        # Set up coordinate transformers
        self.rd_new = pyproj.Proj('EPSG:28992')  # Dutch RD New
        self.wgs84 = pyproj.Proj('EPSG:4326')    # WGS84 (lat/lon)
        self.transformer_to_wgs84 = pyproj.Transformer.from_proj(self.rd_new, self.wgs84, always_xy=True)
        self.transformer_to_rd = pyproj.Transformer.from_proj(self.wgs84, self.rd_new, always_xy=True)
    
    def get_buildings(self, 
                     bbox: Optional[Tuple[float, float, float, float]] = None,
                     max_features: int = 1000,
                     property_name: Optional[str] = None,
                     cql_filter: Optional[str] = None,
                     output_format: str = "application/json",
                     include_geometry: bool = True,
                     convert_to_wgs84: bool = False) -> Dict:
        """
        Request buildings from PDOK WFS service
        
        Args:
            bbox: Bounding box as (min_x, min_y, max_x, max_y) in EPSG:28992
            max_features: Maximum number of features to return
            property_name: Comma-separated list of properties to return
            cql_filter: CQL filter for additional constraints
            output_format: Output format ('application/json' or 'text/xml')
            include_geometry: Whether to include polygon geometry data
            convert_to_wgs84: Convert coordinates from RD New to WGS84
            
        Returns:
            Dictionary containing the response data with enhanced geometry info
        """
        
        params = {
            'service': 'WFS',
            'version': self.version,
            'request': 'GetFeature',
            'typename': self.typename,
            'srsname': self.srs,
            'outputFormat': output_format,
            'count': max_features
        }
        
        # Add bounding box if provided
        if bbox:
            params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{self.srs}"
        
        # Add property filter if provided
        if property_name:
            params['propertyName'] = property_name
            
        # Add CQL filter if provided
        if cql_filter:
            params['cql_filter'] = cql_filter
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            if output_format == "application/json":
                data = response.json()
                
                # Process geometry data if requested
                if include_geometry and 'features' in data:
                    data = self._process_geometry_data(data, convert_to_wgs84)
                
                return data
            else:
                return {"xml_content": response.text}
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            print(f"URL: {response.url if 'response' in locals() else 'N/A'}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response: {response.text[:500]}...")
            raise Exception(f"Failed to fetch buildings data: {str(e)}")
    
    def _process_geometry_data(self, data: Dict, convert_to_wgs84: bool = False) -> Dict:
        """
        Process and enhance geometry data for buildings
        
        Args:
            data: Raw GeoJSON data from PDOK
            convert_to_wgs84: Convert coordinates to WGS84
            
        Returns:
            Enhanced data with geometry information
        """
        for feature in data.get('features', []):
            if 'geometry' in feature and feature['geometry']:
                try:
                    # Create shapely geometry object
                    geom = shape(feature['geometry'])
                    
                    # Convert coordinates if requested
                    if convert_to_wgs84:
                        geom_wgs84 = transform(self.transformer_to_wgs84.transform, geom)
                        feature['geometry'] = geom_wgs84.__geo_interface__
                        feature['coordinate_system'] = 'EPSG:4326'
                    else:
                        feature['coordinate_system'] = 'EPSG:28992'
                    
                    # Add enhanced geometry properties
                    feature['properties']['geometry_info'] = {
                        'area_m2': round(geom.area, 2),
                        'perimeter_m': round(geom.length, 2),
                        'centroid': {
                            'x': round(geom.centroid.x, 2),
                            'y': round(geom.centroid.y, 2)
                        },
                        'bounds': {
                            'min_x': round(geom.bounds[0], 2),
                            'min_y': round(geom.bounds[1], 2),
                            'max_x': round(geom.bounds[2], 2),
                            'max_y': round(geom.bounds[3], 2)
                        },
                        'coordinates_count': len(geom.exterior.coords) if hasattr(geom, 'exterior') else 0
                    }
                    
                    # Convert centroid to WGS84 if requested
                    if convert_to_wgs84:
                        centroid_wgs84 = self.transformer_to_wgs84.transform(geom.centroid.x, geom.centroid.y)
                        feature['properties']['geometry_info']['centroid_wgs84'] = {
                            'lon': round(centroid_wgs84[0], 6),
                            'lat': round(centroid_wgs84[1], 6)
                        }
                
                except Exception as e:
                    feature['properties']['geometry_info'] = {'error': f'Could not process geometry: {str(e)}'}
        
        return data
    
    def convert_coordinates(self, x: float, y: float, to_wgs84: bool = True) -> Tuple[float, float]:
        """
        Convert coordinates between RD New and WGS84
        
        Args:
            x: X coordinate
            y: Y coordinate  
            to_wgs84: If True, convert from RD New to WGS84, else WGS84 to RD New
            
        Returns:
            Tuple of converted coordinates
        """
        if to_wgs84:
            return self.transformer_to_wgs84.transform(x, y)
        else:
            return self.transformer_to_rd.transform(x, y)
    
    def get_building_polygon(self, building_id: str, convert_to_wgs84: bool = False) -> Optional[Dict]:
        """
        Get detailed polygon data for a specific building
        
        Args:
            building_id: Building identification number
            convert_to_wgs84: Convert coordinates to WGS84
            
        Returns:
            Dictionary with building polygon data or None if not found
        """
        cql_filter = f"identificatie='{building_id}'"
        result = self.get_buildings(
            cql_filter=cql_filter,
            max_features=1,
            include_geometry=True,
            convert_to_wgs84=convert_to_wgs84
        )
        
        features = result.get('features', [])
        return features[0] if features else None
    
    def get_buildings_geojson(self, 
                             bbox: Optional[Tuple[float, float, float, float]] = None,
                             max_features: int = 1000,
                             property_name: Optional[str] = None,
                             cql_filter: Optional[str] = None,
                             convert_to_wgs84: bool = True) -> Dict:
        """
        Get buildings as clean GeoJSON for mapping applications
        
        Args:
            bbox: Bounding box as (min_x, min_y, max_x, max_y) in EPSG:28992
            max_features: Maximum number of features to return
            property_name: Comma-separated list of properties to return
            cql_filter: CQL filter for additional constraints
            convert_to_wgs84: Convert coordinates to WGS84 for web mapping (recommended)
            
        Returns:
            Clean GeoJSON FeatureCollection ready for mapping
        """
        data = self.get_buildings(
            bbox=bbox,
            max_features=max_features,
            property_name=property_name,
            cql_filter=cql_filter,
            include_geometry=True,
            convert_to_wgs84=convert_to_wgs84
        )
        
        # Clean up the GeoJSON for mapping
        clean_geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "EPSG:4326" if convert_to_wgs84 else "EPSG:28992"
                }
            },
            "features": []
        }
        
        for feature in data.get('features', []):
            # Create clean feature for mapping
            clean_feature = {
                "type": "Feature",
                "geometry": feature.get('geometry'),
                "properties": {
                    # Keep essential properties
                    "id": feature['properties'].get('identificatie'),
                    "bouwjaar": feature['properties'].get('bouwjaar'),
                    "status": feature['properties'].get('status'),
                    "oppervlakte_min": feature['properties'].get('oppervlakte_min'),
                    "oppervlakte_max": feature['properties'].get('oppervlakte_max'),
                    "aantal_verblijfsobjecten": feature['properties'].get('aantal_verblijfsobjecten'),
                }
            }
            
            # Add geometry info if available
            if 'geometry_info' in feature['properties']:
                geom_info = feature['properties']['geometry_info']
                clean_feature['properties'].update({
                    "area_m2": geom_info.get('area_m2'),
                    "centroid_lat": geom_info.get('centroid_wgs84', {}).get('lat') if convert_to_wgs84 else geom_info.get('centroid', {}).get('y'),
                    "centroid_lon": geom_info.get('centroid_wgs84', {}).get('lon') if convert_to_wgs84 else geom_info.get('centroid', {}).get('x'),
                })
            
            clean_geojson['features'].append(clean_feature)
        
        return clean_geojson
    
    def save_geojson(self, geojson_data: Dict, filename: str) -> None:
        """
        Save GeoJSON data to file
        
        Args:
            geojson_data: GeoJSON data to save
            filename: Output filename (should end with .geojson)
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        print(f"GeoJSON saved to {filename}")
    
    def get_building_coordinates(self, building_id: str, convert_to_wgs84: bool = True) -> Optional[List]:
        """
        Get just the coordinate array for a specific building polygon
        
        Args:
            building_id: Building identification number
            convert_to_wgs84: Convert coordinates to WGS84
            
        Returns:
            List of coordinate pairs [[lon, lat], [lon, lat], ...] or None
        """
        building = self.get_building_polygon(building_id, convert_to_wgs84)
        if building and building.get('geometry'):
            geometry = building['geometry']
            if geometry['type'] == 'Polygon':
                return geometry['coordinates'][0]  # Exterior ring
        return None
    
    def get_buildings_by_municipality(self, 
                                    gemeente_code: str,
                                    max_features: int = 1000,
                                    include_geometry: bool = True) -> Dict:
        """
        Get buildings filtered by municipality code
        
        Args:
            gemeente_code: CBS municipality code
            max_features: Maximum number of features to return
            include_geometry: Whether to include polygon geometry data
            
        Returns:
            Dictionary containing building data with geometry
        """
        cql_filter = f"gemeentecode='{gemeente_code}'"
        return self.get_buildings(cql_filter=cql_filter, max_features=max_features, include_geometry=include_geometry)
    
    def get_buildings_by_postal_code(self, 
                                   postal_code: str,
                                   max_features: int = 1000,
                                   include_geometry: bool = True) -> Dict:
        """
        Get buildings filtered by postal code
        
        Args:
            postal_code: Dutch postal code (e.g., '1234AB')
            max_features: Maximum number of features to return
            include_geometry: Whether to include polygon geometry data
            
        Returns:
            Dictionary containing building data with geometry
        """
        cql_filter = f"postcode='{postal_code}'"
        return self.get_buildings(cql_filter=cql_filter, max_features=max_features, include_geometry=include_geometry)
    
    def get_buildings_in_area(self, 
                             center_x: float, 
                             center_y: float, 
                             radius_m: float,
                             max_features: int = 1000,
                             include_geometry: bool = True) -> Dict:
        """
        Get buildings within a circular area
        
        Args:
            center_x: X coordinate of center point (RD New)
            center_y: Y coordinate of center point (RD New)
            radius_m: Radius in meters
            max_features: Maximum number of features to return
            include_geometry: Whether to include polygon geometry data
            
        Returns:
            Dictionary containing building data with geometry
        """
        # Create bounding box from center point and radius
        bbox = (
            center_x - radius_m,
            center_y - radius_m, 
            center_x + radius_m,
            center_y + radius_m
        )
        
        return self.get_buildings(bbox=bbox, max_features=max_features, include_geometry=include_geometry)
    
    def get_building_properties(self) -> List[str]:
        """
        Get available properties for buildings using DescribeFeatureType
        
        Returns:
            List of available property names
        """
        params = {
            'service': 'WFS',
            'version': self.version,
            'request': 'DescribeFeatureType',
            'typename': self.typename
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML to extract property names
            root = ET.fromstring(response.content)
            properties = []
            
            # Find all element definitions
            for elem in root.iter():
                if elem.tag.endswith('element') and 'name' in elem.attrib:
                    name = elem.attrib['name']
                    if name not in ['geometrie', 'geom']:  # Skip geometry fields
                        properties.append(name)
            
            return properties
            
        except Exception as e:
            print(f"Could not retrieve properties: {str(e)}")
            # Return common BAG pand properties based on documentation
            return [
                'pand', 'identificatie', 'rdf_seealso', 'bouwjaar', 'status', 'gebruiksdoel',
                'oppervlakte_min', 'oppervlakte_max', 'aantal_verblijfsobjecten', 'fuuid'
            ]

# Example usage
def example_usage():
    """
    Example usage of the PDOK Buildings client
    """
    client = PDOKBuildingsClient()
    
    # Example 1: Get buildings in Amsterdam area (approximate center coordinates)
    print("Example 1: Buildings in Amsterdam area")
    buildings = client.get_buildings_in_area(
        center_x=121000,  # Amsterdam center X (RD New)
        center_y=487000,  # Amsterdam center Y (RD New)
        radius_m=1000,    # 1km radius
        max_features=10
    )
    print(f"Found {len(buildings.get('features', []))} buildings")
    
    # Example 2: Get buildings by postal code
    print("\nExample 2: Buildings by postal code")
    buildings_pc = client.get_buildings_by_postal_code("1012AB", max_features=5)
    print(f"Found {len(buildings_pc.get('features', []))} buildings for postal code 1012AB")
    
    # Example 3: Get buildings with specific properties only
    print("\nExample 3: Buildings with specific properties")
    buildings_props = client.get_buildings(
        bbox=(120000, 486000, 122000, 488000),  # Small area in Amsterdam
        property_name="identificatie,bouwjaar,status",
        max_features=5
    )
    
    # Example 4: Get available properties
    print("\nExample 4: Available properties")
    properties = client.get_building_properties()
    print(f"Available properties: {properties[:10]}...")  # Show first 10
    
    # Print sample data from each result set
    if buildings.get('features'):
        print("Sample building data with geometry:")
        for feature in buildings['features'][:2]:
            props = feature['properties']
            print(f"  - ID: {props.get('identificatie', 'N/A')}")
            print(f"    Year: {props.get('bouwjaar', 'N/A')}")
            print(f"    Status: {props.get('status', 'N/A')}")
            if 'geometry_info' in props:
                geom_info = props['geometry_info']
                print(f"    Area: {geom_info.get('area_m2', 'N/A')} m²")
                print(f"    Centroid: ({geom_info.get('centroid', {}).get('x', 'N/A')}, {geom_info.get('centroid', {}).get('y', 'N/A')})")
    
    if buildings_pc.get('features'):
        print("Sample postal code data:")
        for feature in buildings_pc['features'][:2]:
            props = feature['properties']
            print(f"  - ID: {props.get('identificatie', 'N/A')}")
            if 'geometry_info' in props:
                print(f"    Area: {props['geometry_info'].get('area_m2', 'N/A')} m²")
    
    if buildings_props.get('features'):
        print("Sample properties data:")
        for feature in buildings_props['features'][:2]:
            props = feature['properties']
            print(f"  - ID: {props.get('identificatie', 'N/A')}")
            print(f"    Available fields: {list(props.keys())}")
    
    # Example 8: Get specific building polygon
    print("\nExample 8: Detailed polygon for specific building")
    if buildings.get('features'):
        building_id = buildings['features'][0]['properties']['identificatie']
        detailed_building = client.get_building_polygon(building_id, convert_to_wgs84=True)
        if detailed_building:
            props = detailed_building['properties']
            geom_info = props.get('geometry_info', {})
            print(f"Building {building_id}:")
            print(f"  - Area: {geom_info.get('area_m2')} m²")
            print(f"  - Perimeter: {geom_info.get('perimeter_m')} m")
            print(f"  - Centroid (WGS84): {geom_info.get('centroid_wgs84', 'N/A')}")
            print(f"  - Coordinate count: {geom_info.get('coordinates_count')}")
    
    # Example 9: Convert coordinates
    print("\nExample 9: Coordinate conversion")
    rd_x, rd_y = 121000, 487000  # Amsterdam center in RD New
    wgs84_lon, wgs84_lat = client.convert_coordinates(rd_x, rd_y, to_wgs84=True)
    print(f"RD New ({rd_x}, {rd_y}) = WGS84 ({wgs84_lon:.6f}, {wgs84_lat:.6f})")
    
    # Convert back
    rd_x_back, rd_y_back = client.convert_coordinates(wgs84_lon, wgs84_lat, to_wgs84=False)
    print(f"WGS84 ({wgs84_lon:.6f}, {wgs84_lat:.6f}) = RD New ({rd_x_back:.1f}, {rd_y_back:.1f})")
    
    # Example 10: Get clean GeoJSON for mapping
    print("\nExample 10: Clean GeoJSON for mapping")
    geojson_data = client.get_buildings_geojson(
        bbox=(120000, 486000, 122000, 488000),
        max_features=5,
        convert_to_wgs84=True  # Essential for web mapping
    )
    
    print(f"GeoJSON contains {len(geojson_data['features'])} buildings")
    print("Sample GeoJSON feature:")
    if geojson_data['features']:
        sample_feature = geojson_data['features'][0]
        print(f"  - Building ID: {sample_feature['properties']['id']}")
        print(f"  - Coordinates: {len(sample_feature['geometry']['coordinates'][0])} points")
        print(f"  - Area: {sample_feature['properties']['area_m2']} m²")
        print(f"  - Centroid: [{sample_feature['properties']['centroid_lon']:.6f}, {sample_feature['properties']['centroid_lat']:.6f}]")
    
    # Save GeoJSON file for use in mapping applications
    client.save_geojson(geojson_data, "amsterdam_buildings.geojson")
    print("  → Saved to amsterdam_buildings.geojson (ready for QGIS, Leaflet, etc.)")
    
    return buildings

# Additional usage examples
def advanced_examples():
    """
    More advanced usage examples
    """
    client = PDOKBuildingsClient()
    
    # Example 5: Filter by construction year with geometry
    print("Example 5: Buildings built after 2000 with area info")
    modern_buildings = client.get_buildings(
        bbox=(120000, 486000, 122000, 488000),
        cql_filter="bouwjaar > 2000",
        max_features=5,
        include_geometry=True
    )
    
    for building in modern_buildings.get('features', []):
        props = building['properties']
        geom_info = props.get('geometry_info', {})
        print(f"  - Built: {props.get('bouwjaar')}, Area: {geom_info.get('area_m2', 'N/A')} m²")
    
    # Example 6: Get buildings with WGS84 coordinates
    print("\nExample 6: Buildings with WGS84 coordinates")
    buildings_wgs84 = client.get_buildings(
        bbox=(120000, 486000, 122000, 488000),
        property_name="identificatie,bouwjaar,oppervlakte_min,oppervlakte_max,aantal_verblijfsobjecten",
        max_features=3,
        include_geometry=True,
        convert_to_wgs84=True
    )
    
    for building in buildings_wgs84.get('features', []):
        props = building['properties']
        geom_info = props.get('geometry_info', {})
        print(f"  - ID: {props.get('identificatie')}")
        print(f"    Year: {props.get('bouwjaar')}")
        print(f"    Area: {geom_info.get('area_m2')} m²")
        print(f"    Centroid WGS84: {geom_info.get('centroid_wgs84', 'N/A')}")
        print(f"    Units: {props.get('aantal_verblijfsobjecten')}")
    
    # Example 7: Large buildings analysis
    print("\nExample 7: Large buildings (> 500 m²)")
    large_buildings = client.get_buildings(
        bbox=(120000, 486000, 125000, 490000),  # Larger area
        max_features=10,
        include_geometry=True
    )
    
    large_building_list = []
    for building in large_buildings.get('features', []):
        props = building['properties']
        geom_info = props.get('geometry_info', {})
        area = geom_info.get('area_m2', 0)
        if area > 500:
            large_building_list.append({
                'id': props.get('identificatie'),
                'year': props.get('bouwjaar'),
                'area': area
            })
    
    # Sort by area
    large_building_list.sort(key=lambda x: x['area'], reverse=True)
    
    print(f"Found {len(large_building_list)} buildings > 500 m²:")
    for building in large_building_list[:5]:
        print(f"  - {building['area']} m² (built {building['year']}) - ID: {building['id']}")

def create_leaflet_map_example():
    """
    Create a simple HTML file with Leaflet map showing buildings
    """
    client = PDOKBuildingsClient()
    
    # Get buildings around Amsterdam Central Station
    geojson_data = client.get_buildings_geojson(
        bbox=(120500, 487500, 121500, 488500),  # Area around Amsterdam Central
        max_features=50,
        convert_to_wgs84=True
    )
    
    # Create HTML with Leaflet map
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PDOK Buildings Map</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        #map {{ height: 600px; width: 100%; }}
        .building-popup {{ font-family: Arial, sans-serif; }}
    </style>
</head>
<body>
    <h1>Amsterdam Buildings from PDOK</h1>
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Initialize map
        var map = L.map('map').setView([52.3795, 4.9003], 15); // Amsterdam Central
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // Building data from PDOK
        var buildingsData = {json.dumps(geojson_data, indent=2)};
        
        // Style function for buildings
        function buildingStyle(feature) {{
            var year = feature.properties.bouwjaar || 2000;
            var color = year < 1900 ? '#8B0000' :  // Dark red for historic
                       year < 1950 ? '#FF4500' :  // Orange red
                       year < 2000 ? '#32CD32' :  // Green
                       '#1E90FF';                 // Blue for modern
            
            return {{
                fillColor: color,
                weight: 1,
                opacity: 1,
                color: 'white',
                fillOpacity: 0.7
            }};
        }}
        
        // Add buildings to map
        L.geoJSON(buildingsData, {{
            style: buildingStyle,
            onEachFeature: function (feature, layer) {{
                var props = feature.properties;
                var popupContent = '<div class="building-popup">' +
                    '<strong>Building Info</strong><br>' +
                    'ID: ' + (props.id || 'N/A') + '<br>' +
                    'Year: ' + (props.bouwjaar || 'Unknown') + '<br>' +
                    'Status: ' + (props.status || 'N/A') + '<br>' +
                    'Area: ' + (props.area_m2 || 'N/A') + ' m²<br>' +
                    'Units: ' + (props.aantal_verblijfsobjecten || 'N/A') +
                    '</div>';
                layer.bindPopup(popupContent);
            }}
        }}).addTo(map);
        
        console.log('Loaded', buildingsData.features.length, 'buildings');
    </script>
</body>
</html>
"""
    
    # Save HTML file
    with open('buildings_map.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created interactive map: buildings_map.html")
    print(f"   - {len(geojson_data['features'])} buildings loaded")
    print(f"   - Buildings colored by construction year")
    print(f"   - Click buildings for details")
    print(f"   - Open buildings_map.html in your browser!")
    
    return geojson_data

if __name__ == "__main__":
    example_usage()
    print("\n" + "="*50)
    print("ADVANCED EXAMPLES")
    print("="*50)
    advanced_examples()
    print("\n" + "="*50)
    print("CREATING INTERACTIVE MAP")
    print("="*50)
    create_leaflet_map_example()