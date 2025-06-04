# tools/coordinate_conversion_tool.py

import math
from smolagents import Tool
from typing import Dict, Tuple
from pyproj import Transformer

class CoordinateConversionTool(Tool):
    """
    Tool for converting WGS84 coordinates to RD New (Dutch national grid system).
    Uses pyproj for EPSG:4326 → EPSG:28992 transformation.
    """

    name = "convert_coordinates_to_rd_new"
    description = """Convert WGS84 coordinates (latitude, longitude) to RD New coordinates (X, Y).

    This tool is ESSENTIAL for making PDOK WFS requests, as PDOK services use the Dutch RD New 
    coordinate system (EPSG:28992), not WGS84 (EPSG:4326).
    
    Use this tool to:
    - Convert location coordinates found by search_location_coordinates
    - Create proper bounding boxes for PDOK requests
    - Ensure spatial queries work correctly with Dutch data
    
    Returns RD New X, Y coordinates in meters.
    """

    inputs = {
        "latitude": {
            "type": "number",
            "description": "WGS84 latitude in decimal degrees"
        },
        "longitude": {
            "type": "number",
            "description": "WGS84 longitude in decimal degrees"
        }
    }

    output_type = "object"
    is_initialized = True

    def forward(self, latitude: float, longitude: float) -> Dict:
        """Convert WGS84 coordinates to RD New using pyproj."""
        try:
            print(f"🔄 Converting WGS84 ({longitude:.6f}, {latitude:.6f}) to RD New...")

            # Validate input coordinates are in Netherlands bounds
            if not (50.5 <= latitude <= 54.0 and 3.0 <= longitude <= 7.5):
                return {
                    "error": f"Coordinates ({latitude}, {longitude}) are outside Netherlands bounds"
                }

            rd_x, rd_y = self._wgs84_to_rd_new(latitude, longitude)

            print(f"✅ RD New coordinates: X={rd_x:.2f}, Y={rd_y:.2f}")

            radius_m = 1000
            bbox_min_x = rd_x - radius_m
            bbox_min_y = rd_y - radius_m
            bbox_max_x = rd_x + radius_m
            bbox_max_y = rd_y + radius_m
            bbox_rd = f"{bbox_min_x},{bbox_min_y},{bbox_max_x},{bbox_max_y}"

            return {
                "rd_x": rd_x,
                "rd_y": rd_y,
                "bbox_rd_1km": bbox_rd,
                "coordinate_system": "EPSG:28992",
                "original_wgs84": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "bbox_explanation": "Bounding box with 1km radius around the point in RD New coordinates"
            }

        except Exception as e:
            return {"error": f"Coordinate conversion failed: {str(e)}"}

    def _wgs84_to_rd_new(self, lat: float, lon: float) -> Tuple[float, float]:
        """Use pyproj to convert WGS84 to RD New (EPSG:28992)."""
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
        return transformer.transform(lon, lat)


class CreateRDBoundingBoxTool(Tool):
    """
    Tool for creating bounding boxes in RD New coordinates around a center point.
    Essential for PDOK spatial queries.
    """
    
    name = "create_rd_bounding_box"
    description = """Create a bounding box in RD New coordinates around a center point.
    
    Use this tool to create spatial filters for PDOK WFS requests.
    PDOK services require bounding boxes in RD New coordinate system (EPSG:28992).
    
    Returns a bbox string in format: "min_x,min_y,max_x,max_y" suitable for PDOK WFS requests."""
    
    inputs = {
        "rd_x": {
            "type": "number",
            "description": "RD New X coordinate (from coordinate conversion)"
        },
        "rd_y": {
            "type": "number",
            "description": "RD New Y coordinate (from coordinate conversion)"
        },
        "radius_km": {
            "type": "number",
            "description": "Radius in kilometers (default: 1.0)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def forward(self, rd_x: float, rd_y: float, radius_km: float = 1.0) -> Dict:
        """Create RD New bounding box around center point."""
        try:
            print(f"📦 Creating RD New bbox around ({rd_x:.2f}, {rd_y:.2f}) with {radius_km}km radius")
            
            # Convert radius to meters
            radius_m = radius_km * 1000
            
            # Calculate bounding box
            min_x = rd_x - radius_m
            min_y = rd_y - radius_m
            max_x = rd_x + radius_m
            max_y = rd_y + radius_m
            
            # Create bbox string for PDOK WFS
            bbox_string = f"{min_x},{min_y},{max_x},{max_y}"
            
            print(f"✅ RD New bbox: {bbox_string}")
            
            return {
                "bbox": bbox_string,
                "min_x": min_x,
                "min_y": min_y, 
                "max_x": max_x,
                "max_y": max_y,
                "radius_km": radius_km,
                "radius_m": radius_m,
                "coordinate_system": "EPSG:28992",
                "usage": "Use this bbox string directly in PDOK WFS requests"
            }
            
        except Exception as e:
            return {"error": f"Bounding box creation failed: {str(e)}"}


# Export tools for use in app.py
#__all__ = ["CoordinateConversionTool", "CreateRDBoundingBoxTool"]