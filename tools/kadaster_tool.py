# kadaster_tool.py - Dutch Land Registry (Kadaster) Integration

import requests
import json
from smolagents import Tool
from datetime import datetime
from typing import Optional, List, Dict
import pyproj

class KadasterBRKTool(Tool):
    """
    Access Dutch Kadaster BRK (Basisregistratie Kadaster) for land parcels and ownership data.
    
    Note: This uses the free PDOK WFS service. For detailed ownership information,
    you may need to use the paid Kadaster BRK Bevragen API.
    """
    
    name = "get_kadaster_parcels"
    description = "Get Dutch land parcels (kadaster) data from BRK including basic ownership information"
    inputs = {
        "location": {"type": "string", "description": "Location name (e.g., 'Amsterdam', 'Utrecht')"},
        "radius_km": {"type": "number", "description": "Search radius in kilometers", "nullable": True},
        "max_features": {"type": "integer", "description": "Maximum parcels to return", "nullable": True},
        "parcel_type": {"type": "string", "description": "Type of parcel to search for", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # PDOK BRK WFS service (free, basic data)
        self.brk_url = "https://service.pdok.nl/lv/brk/wfs/v2_0"
        # BGT for detailed parcel boundaries
        self.bgt_url = "https://service.pdok.nl/lv/bgt/wfs/v1_0"
        self.srs = "EPSG:28992"  # Dutch RD New coordinate system
        
        # Initialize coordinate transformers
        try:
            import pyproj
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
            self.transformer_to_rd = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
            print("✅ Kadaster coordinate transformers initialized")
        except ImportError:
            print("⚠️ PyProj not available for Kadaster tool")
            self.transformer_to_wgs84 = None
            self.transformer_to_rd = None
    
    def forward(self, location, radius_km=5.0, max_features=50, parcel_type=None):
        """Get Kadaster land parcels with basic ownership information."""
        
        try:
            print(f"\n🏛️ === KADASTER BRK SEARCH ===")
            print(f"Location: {location}")
            print(f"Radius: {radius_km}km")
            print(f"Max features: {max_features}")
            
            # Step 1: Get location coordinates
            from app import find_location_coordinates
            loc_data = find_location_coordinates(location)
            if "error" in loc_data:
                return {
                    "text_description": f"❌ Could not find coordinates for {location}",
                    "geojson_data": [],
                    "error": loc_data["error"]
                }
            
            lat, lon = loc_data["lat"], loc_data["lon"]
            print(f"✅ Found coordinates: {lat:.6f}, {lon:.6f}")
            
            # Step 2: Convert to RD New coordinates
            if self.transformer_to_rd:
                center_x, center_y = self.transformer_to_rd.transform(lon, lat)
                radius_m = radius_km * 1000
                bbox = [center_x - radius_m, center_y - radius_m, center_x + radius_m, center_y + radius_m]
                print(f"✅ Converted to RD New: {center_x:.2f}, {center_y:.2f}")
            else:
                return {
                    "text_description": "❌ Coordinate transformation not available for Kadaster queries",
                    "geojson_data": [],
                    "error": "PyProj required for Kadaster coordinate transformation"
                }
            
            # Step 3: Query BRK for cadastral parcels
            parcels_data = self._get_brk_parcels(bbox, max_features)
            
            if not parcels_data:
                return {
                    "text_description": f"❌ No cadastral parcels found in {location}",
                    "geojson_data": [],
                    "error": "No parcels found"
                }
            
            print(f"📦 Found {len(parcels_data)} cadastral parcels")
            
            # Step 4: Process parcels and add basic ownership info
            processed_parcels = []
            for i, parcel in enumerate(parcels_data):
                try:
                    processed_parcel = self._process_parcel(parcel, i)
                    if processed_parcel:
                        processed_parcels.append(processed_parcel)
                        print(f"✅ Processed parcel {i+1}: {processed_parcel['name']}")
                except Exception as e:
                    print(f"❌ Error processing parcel {i+1}: {e}")
                    continue
            
            if not processed_parcels:
                return {
                    "text_description": f"❌ No valid parcels could be processed for {location}",
                    "geojson_data": [],
                    "error": "No valid parcels processed"
                }
            
            # Step 5: Create response
            text_description = self._create_parcel_description(location, processed_parcels)
            
            return {
                "text_description": text_description,
                "geojson_data": processed_parcels
            }
            
        except Exception as e:
            error_msg = f"Kadaster tool error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "text_description": f"❌ Error retrieving cadastral data: {error_msg}",
                "geojson_data": [],
                "error": error_msg
            }
    
    def _get_brk_parcels(self, bbox, max_features):
        """Query BRK WFS service for cadastral parcels."""
        
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': 'brk:perceel',  # Cadastral parcel layer
            'outputFormat': 'application/json',
            'srsName': self.srs,
            'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{self.srs}",
            'count': max_features
        }
        
        print(f"🌐 Querying BRK WFS: {self.brk_url}")
        
        try:
            response = requests.get(self.brk_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('features', [])
        except requests.exceptions.RequestException as e:
            print(f"❌ BRK WFS request failed: {e}")
            return []
    
    def _process_parcel(self, parcel_feature, index):
        """Process individual cadastral parcel."""
        
        props = parcel_feature.get('properties', {})
        geometry = parcel_feature.get('geometry', {})
        
        if not geometry:
            return None
        
        # Extract parcel information
        parcel_id = props.get('identificatie', f'Parcel_{index+1}')
        gemeente = props.get('gemeente', 'Unknown municipality')
        sectie = props.get('sectie', 'Unknown section')
        perceelnummer = props.get('perceelnummer', 'Unknown')
        
        # Calculate centroid
        centroid_rd = self._calculate_centroid(geometry)
        if not centroid_rd:
            return None
        
        # Convert to WGS84
        if self.transformer_to_wgs84:
            centroid_wgs84 = self.transformer_to_wgs84.transform(centroid_rd[0], centroid_rd[1])
            lat, lon = centroid_wgs84[1], centroid_wgs84[0]
        else:
            return None
        
        # Convert geometry to WGS84
        wgs84_geometry = self._convert_geometry_to_wgs84(geometry)
        
        # Calculate area (rough approximation)
        area_m2 = self._calculate_area(geometry)
        
        # Create parcel name
        parcel_name = f"{gemeente} {sectie}-{perceelnummer}"
        
        # Basic ownership info (limited in free PDOK service)
        ownership_info = props.get('zakelijkrecht', 'Unknown ownership')
        
        description_parts = [
            f"Municipality: {gemeente}",
            f"Section: {sectie}",
            f"Parcel: {perceelnummer}",
            f"Area: ~{area_m2:.0f}m²"
        ]
        
        if ownership_info and ownership_info != 'Unknown ownership':
            description_parts.append(f"Rights: {ownership_info}")
        
        return {
            "name": parcel_name,
            "lat": lat,
            "lon": lon,
            "description": " | ".join(description_parts),
            "geometry": wgs84_geometry,
            "properties": {
                "parcel_id": parcel_id,
                "gemeente": gemeente,
                "sectie": sectie,
                "perceelnummer": perceelnummer,
                "area_m2": area_m2,
                "ownership_info": ownership_info,
                "centroid_lat": lat,
                "centroid_lon": lon,
                **props  # Include all original properties
            }
        }
    
    def _calculate_centroid(self, geometry):
        """Calculate centroid of geometry in RD New coordinates."""
        if geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            if coords and len(coords) > 0:
                avg_x = sum(coord[0] for coord in coords) / len(coords)
                avg_y = sum(coord[1] for coord in coords) / len(coords)
                return [avg_x, avg_y]
        elif geometry['type'] == 'Point':
            return geometry['coordinates']
        return None
    
    def _convert_geometry_to_wgs84(self, geometry):
        """Convert geometry from RD New to WGS84."""
        if not self.transformer_to_wgs84:
            return geometry
        
        if geometry['type'] == 'Polygon':
            wgs84_coords = []
            for ring in geometry['coordinates']:
                wgs84_ring = []
                for coord in ring:
                    wgs84_coord = self.transformer_to_wgs84.transform(coord[0], coord[1])
                    wgs84_ring.append([wgs84_coord[0], wgs84_coord[1]])
                wgs84_coords.append(wgs84_ring)
            return {
                'type': 'Polygon',
                'coordinates': wgs84_coords
            }
        elif geometry['type'] == 'Point':
            wgs84_coord = self.transformer_to_wgs84.transform(geometry['coordinates'][0], geometry['coordinates'][1])
            return {
                'type': 'Point',
                'coordinates': [wgs84_coord[0], wgs84_coord[1]]
            }
        
        return geometry
    
    def _calculate_area(self, geometry):
        """Calculate approximate area of polygon."""
        if geometry['type'] != 'Polygon':
            return 50  # Default area for non-polygons
        
        coords = geometry['coordinates'][0]
        if not coords or len(coords) < 3:
            return 50
        
        # Shoelace formula for area calculation
        n = len(coords)
        area = 0.5 * abs(sum(coords[i][0] * coords[(i + 1) % n][1] - 
                           coords[(i + 1) % n][0] * coords[i][1] 
                           for i in range(n)))
        return area
    
    def _create_parcel_description(self, location, parcels):
        """Create text description of cadastral parcels."""
        
        total_area = sum(p['properties']['area_m2'] for p in parcels)
        municipalities = set(p['properties']['gemeente'] for p in parcels)
        
        text_parts = [f"## Cadastral Parcels in {location} (Kadaster Data)"]
        text_parts.append(f"\nI found **{len(parcels)} cadastral parcels** in {location} from the Dutch Kadaster (BRK) database.")
        
        if total_area > 0:
            text_parts.append(f"\n**Total area**: {total_area:,.0f}m² ({total_area/10000:.1f} hectares)")
        
        if len(municipalities) > 1:
            text_parts.append(f"\n**Municipalities**: {', '.join(sorted(municipalities))}")
        
        # Add sample parcels
        text_parts.append(f"\n**Notable parcels include**:")
        for i, parcel in enumerate(parcels[:5]):  # Show top 5
            props = parcel['properties']
            gemeente = props.get('gemeente', 'Unknown')
            area = props.get('area_m2', 0)
            text_parts.append(f"* **{parcel['name']}** - {gemeente}, {area:.0f}m²")
        
        text_parts.append(f"\n⚠️ **Note**: This shows basic cadastral information from free PDOK services. For detailed ownership information, premium Kadaster APIs are required.")
        text_parts.append(f"\nAll **{len(parcels)} parcels** are displayed on the map. Click any parcel for details.")
        
        return "\n".join(text_parts)


# Contact History Tool for tracking landowner communications
class ContactHistoryTool(Tool):
    """Manage contact history with land owners."""
    
    name = "manage_contact_history"
    description = "Track and manage contact history with property owners"
    inputs = {
        "action": {"type": "string", "description": "Action: 'check' or 'add' or 'list'"},
        "owner_id": {"type": "string", "description": "Owner identifier", "nullable": True},
        "contact_date": {"type": "string", "description": "Contact date (YYYY-MM-DD)", "nullable": True},
        "notes": {"type": "string", "description": "Contact notes", "nullable": True}
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        # Simple in-memory storage for demo (use proper database in production)
        self.contact_history = {}
    
    def forward(self, action, owner_id=None, contact_date=None, notes=None):
        """Manage contact history with property owners."""
        
        if action == "check":
            if owner_id:
                contacted = owner_id in self.contact_history
                return {
                    "owner_id": owner_id,
                    "contacted": contacted,
                    "last_contact": self.contact_history.get(owner_id, {}).get('last_contact'),
                    "contact_count": len(self.contact_history.get(owner_id, {}).get('contacts', []))
                }
            else:
                return {
                    "total_owners_contacted": len(self.contact_history),
                    "contacted_owners": list(self.contact_history.keys())
                }
        
        elif action == "add" and owner_id:
            if owner_id not in self.contact_history:
                self.contact_history[owner_id] = {"contacts": []}
            
            contact_record = {
                "date": contact_date or datetime.now().strftime("%Y-%m-%d"),
                "notes": notes or "Contact recorded"
            }
            
            self.contact_history[owner_id]["contacts"].append(contact_record)
            self.contact_history[owner_id]["last_contact"] = contact_record["date"]
            
            return {
                "success": True,
                "owner_id": owner_id,
                "contact_added": contact_record
            }
        
        elif action == "list":
            return {
                "contact_history": self.contact_history
            }
        
        return {"error": "Invalid action or missing parameters"}


# Example usage in app.py:
"""
# Add to your app.py

from kadaster_tool import KadasterBRKTool, ContactHistoryTool

# Add to your agent tools list
def create_agent_with_yaml_prompt():
    tools = [
        find_location_coordinates,
        analyze_current_map_features,
        get_map_context_info,
        answer_map_question,
        PDOKBuildingsRealTool(),
        KadasterBRKTool(),           # NEW: Cadastral parcels
        ContactHistoryTool(),        # NEW: Contact management
        DuckDuckGoSearchTool()
    ]
    # ... rest of function
"""