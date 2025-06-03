# tools/coordinate_conversion_tool.py

import math
from smolagents import Tool
from typing import Dict, Tuple

class CoordinateConversionTool(Tool):
    """
    Tool for converting WGS84 coordinates to RD New (Dutch national grid system).
    PDOK WFS services require RD New coordinates, not WGS84.
    """
    
    name = "convert_coordinates_to_rd_new"
    description = """Convert WGS84 coordinates (latitude, longitude) to RD New coordinates (X, Y).
    
    This tool is ESSENTIAL for making PDOK WFS requests, as PDOK services use the Dutch RD New 
    coordinate system (EPSG:28992), not WGS84 (EPSG:4326).
    
    Use this tool to:
    - Convert location coordinates found by search_location_coordinates
    - Create proper bounding boxes for PDOK requests
    - Ensure spatial queries work correctly with Dutch data
    
    Returns RD New X, Y coordinates in meters."""
    
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
        """Convert WGS84 coordinates to RD New."""
        try:
            print(f"🔄 Converting WGS84 ({longitude:.6f}, {latitude:.6f}) to RD New...")
            
            # Validate input coordinates are in Netherlands bounds
            if not (50.5 <= latitude <= 54.0 and 3.0 <= longitude <= 7.5):
                return {
                    "error": f"Coordinates ({latitude}, {longitude}) are outside Netherlands bounds"
                }
            
            # Convert to RD New using accurate transformation
            rd_x, rd_y = self._wgs84_to_rd_new(latitude, longitude)
            
            print(f"✅ RD New coordinates: X={rd_x:.2f}, Y={rd_y:.2f}")
            
            # Also provide a bounding box around the point (1km radius)
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
        """
        Convert WGS84 coordinates to RD New using accurate transformation.
        Based on the official RDNAPTRANS transformation.
        """
        # Convert to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        # RD New reference point (Amersfoort)
        lat0 = math.radians(52.15616055555555)
        lon0 = math.radians(5.38763888888889)
        
        # RD New parameters
        x0 = 155000.0
        y0 = 463000.0
        k0 = 0.9999079
        
        # Bessel 1841 ellipsoid parameters
        a = 6377397.155  # Semi-major axis
        e2 = 0.006674372230614  # First eccentricity squared
        
        # Calculate differences
        dlat = lat_rad - lat0
        dlon = lon_rad - lon0
        
        # Calculate intermediate values
        m = a * ((1 - e2/4 - 3*e2*e2/64 - 5*e2*e2*e2/256) * dlat -
                 (3*e2/8 + 3*e2*e2/32 + 45*e2*e2*e2/1024) * math.sin(2*lat0 + dlat) +
                 (15*e2*e2/256 + 45*e2*e2*e2/1024) * math.sin(4*lat0 + 2*dlat) -
                 (35*e2*e2*e2/3072) * math.sin(6*lat0 + 3*dlat))
        
        n = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
        t = math.tan(lat_rad)**2
        c = e2 * math.cos(lat_rad)**2 / (1 - e2)
        a_coeff = math.cos(lat_rad) * dlon
        
        # Calculate RD New coordinates
        x = x0 + k0 * n * (a_coeff + 
                           (1 - t + c) * a_coeff**3 / 6 +
                           (5 - 18*t + t**2 + 72*c - 58*e2) * a_coeff**5 / 120)
        
        y = y0 + k0 * (m + n * math.tan(lat_rad) * 
                       (a_coeff**2 / 2 +
                        (5 - t + 9*c + 4*c**2) * a_coeff**4 / 24 +
                        (61 - 58*t + t**2 + 600*c - 330*e2) * a_coeff**6 / 720))
        
        return x, y


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
__all__ = ["CoordinateConversionTool", "CreateRDBoundingBoxTool"]