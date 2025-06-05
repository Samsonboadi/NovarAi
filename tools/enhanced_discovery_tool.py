# tools/enhanced_discovery_tool.py - FIXED VERSION

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple

class IntentDrivenPDOKDiscoveryTool(Tool):
    """
    FIXED: Complete enhanced PDOK service discovery with correct coordinate systems
    and robust sample data analysis.
    """
    
    name = "discover_pdok_services"
    description = """Discover specific PDOK WFS services with intelligent attribute analysis.

        This enhanced tool provides complete discovery capabilities:
        1. Service discovery based on user intent
        2. Attribute schema discovery 
        3. Sample data analysis to understand actual values
        4. Intelligent filter recommendations
        5. Value-based guidance for query construction
        6. Use sample size of 25 to limit API calls

        FIXED ISSUES:
        - Correct coordinate system configurations
        - Robust coordinate transformations  
        - Better sample data analysis
        - Improved error handling

        Returns comprehensive analysis including actual attribute values for intelligent filtering."""
    
    inputs = {
        "service_name": {
            "type": "string", 
            "description": "Specific service to discover: 'bestandbodemgebruik', 'bag', 'cadastral', 'natura2000', 'cbs', 'bgt', 'wetlands', or 'all'"
        },
        "get_attributes": {
            "type": "boolean",
            "description": "Whether to get detailed attribute information (default: True)",
            "nullable": True
        },
        "sample_data": {
            "type": "boolean",
            "description": "Whether to sample actual data to understand attribute values (default: True)",
            "nullable": True
        },
        "location_center": {
            "type": "object",
            "description": "Center point as list [lat, lon] for sampling data (optional)",
            "nullable": True
        },
        "sample_size": {
            "type": "integer",
            "description": "Number of features to sample for analysis (default: 25)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        
        # FIXED: Correct coordinate systems for each service
        self.services = {
            "bestandbodemgebruik": {
                "name": "CBS - Land Use Database (Bestand Bodemgebruik)",
                "url": "https://service.pdok.nl/cbs/bestandbodemgebruik/2015/wfs/v1_0",
                "description": "Detailed land use classification for the Netherlands from 2015",
                "coordinate_system": "EPSG:28992",  # FIXED: Uses RD New, not WGS84
                "primary_layer": "bestandbodemgebruik:bestand_bodemgebruik_2015",
                "analysis_focus": "land_use_classification",
                "expected_classification_fields": ["bodemgebruik", "categorie"],
                "expected_area_fields": ["shape_area"],
                "key_attributes": {
                    "expected": ["bodemgebruik", "categorie", "bg2015"],
                    "description": "Land use classification and category information"
                }
            },
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "description": "Dutch Buildings and Addresses Database",
                "coordinate_system": "EPSG:28992",  # RD New
                "primary_layer": "bag:pand",
                "analysis_focus": "building_characteristics",
                "expected_classification_fields": ["status", "pandstatus"],
                "expected_area_fields": ["oppervlakte"],
                "expected_temporal_fields": ["bouwjaar"],
                "key_attributes": {
                    "expected": ["bouwjaar", "oppervlakte", "status"],
                    "description": "Building construction year, area, and status information"
                }
            },
            "cadastral": {
                "name": "Cadastral Map - Kadastrale Kaart v5",
                "url": "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0",
                "description": "Cadastral parcel boundaries and reference information",
                "coordinate_system": "EPSG:28992",  # RD New
                "primary_layer": "kadastralekaart:Perceel",
                "analysis_focus": "parcel_properties",
                "expected_area_fields": ["kadastraleGrootteWaarde"],
                "expected_classification_fields": ["perceeltype"],
                "key_attributes": {
                    "expected": ["kadastraleGrootteWaarde", "perceelnummer"],
                    "description": "Parcel area and identification"
                }
            },
            "natura2000": {
                "name": "Natura 2000 - Protected Nature Areas",
                "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
                "description": "EU protected natural areas network",
                "coordinate_system": "EPSG:28992",  # RD New
                "primary_layer": "natura2000:natura2000",
                "analysis_focus": "environmental_protection",
                "expected_classification_fields": ["type_gebied", "naam"],
                "key_attributes": {
                    "expected": ["naam", "gebiedsnaam", "type_gebied"],
                    "description": "Protected area names and types"
                }
            },
            "cbs": {
                "name": "CBS - Administrative Boundaries",
                "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
                "description": "Administrative boundaries and statistical areas",
                "coordinate_system": "EPSG:28992",  # RD New
                "primary_layer": "wijkenbuurten:cbs_gemeente_2023_gegeneraliseerd",
                "analysis_focus": "administrative_boundaries",
                "expected_classification_fields": ["gemeentenaam", "provincienaam"],
                "key_attributes": {
                    "expected": ["gemeentenaam", "provincienaam", "gemeentecode"],
                    "description": "Municipality and province information"
                }
            }
        }
    
    def forward(self, service_name: str, get_attributes: Optional[bool] = True, 
                sample_data: Optional[bool] = True, location_center: Optional[Union[List[float], Dict]] = None,
                sample_size: Optional[int] = 25) -> Dict:
        """FIXED: Discover specific PDOK service with robust error handling."""
        try:
            print(f"🎯 FIXED Enhanced PDOK discovery: {service_name}")
            
            # Handle aliases
            if service_name in ["landuse", "land_use", "bodemgebruik"]:
                service_name = "bestandbodemgebruik"
            
            if service_name not in self.services:
                available_services = list(self.services.keys())
                return {
                    "error": f"Unknown service: {service_name}. Available: {available_services}",
                    "available_services": available_services
                }
            
            return self._discover_single_service(service_name, get_attributes, sample_data, location_center, sample_size)
                
        except Exception as e:
            error_msg = f"Enhanced discovery error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "discovery_success": False}
    
    def _discover_single_service(self, service_name: str, get_attributes: bool, 
                                sample_data: bool, location_center: Optional[Union[List[float], Dict]], 
                                sample_size: int) -> Dict:
        """FIXED: Discover service with proper error handling."""
        config = self.services[service_name]
        
        print(f"📡 Discovering {service_name}: {config['name']}")
        
        # Step 1: Basic service capabilities
        capabilities = self._get_service_capabilities(config["url"], get_attributes)
        
        if capabilities.get('error'):
            return {"error": f"Could not access service: {capabilities['error']}", "discovery_success": False}
        
        # Step 2: Sample data analysis (if requested)
        sample_analysis = {"sample_success": False}
        if sample_data:
            print(f"🧪 Sampling data for attribute value analysis...")
            sample_analysis = self._analyze_sample_data(config, location_center, sample_size)
        
        # Step 3: Intelligent recommendations
        print(f"🧠 Generating intelligent filter recommendations...")
        recommendations = self._generate_filter_recommendations(config, sample_analysis, capabilities)
        
        result = {
            "service": {
                **config,
                "capabilities": capabilities,
                "available": True
            },
            "sample_analysis": sample_analysis,
            "filter_recommendations": recommendations,
            "discovery_method": "enhanced_with_sample_analysis",
            "discovery_success": True
        }
        
        return result
    
    def _get_service_capabilities(self, service_url: str, get_attributes: bool) -> Dict:
        """Get service capabilities and attributes."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            print(f"  📡 Requesting capabilities from: {service_url}")
            response = requests.get(service_url, params=params, timeout=15)
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
                        
                        # Get attributes if requested
                        if get_attributes and self._is_primary_layer(name_elem.text):
                            print(f"  🔬 Getting attributes for: {name_elem.text}")
                            attributes = self._get_layer_attributes(service_url, name_elem.text)
                            layer_info["attributes"] = attributes
                        
                        layers.append(layer_info)
            
            return {
                "layers": layers,
                "layer_count": len(layers),
                "service_operational": True
            }
            
        except Exception as e:
            error_msg = f"Could not get capabilities: {str(e)}"
            print(f"  ❌ {error_msg}")
            return {"error": error_msg}
    
    def _analyze_sample_data(self, config: Dict, location_center: Optional[Union[List[float], Dict]], 
                            sample_size: int) -> Dict:
        """FIXED: Sample data with robust coordinate handling."""
        try:
            service_url = config["url"]
            layer_name = config["primary_layer"]
            coordinate_system = config["coordinate_system"]
            
            print(f"   🌐 Sampling from: {service_url}")
            print(f"   📦 Layer: {layer_name}")
            print(f"   📊 Sample size: {sample_size}")
            print(f"   🗺️ Coordinate system: {coordinate_system}")
            
            # Build sample request parameters
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': layer_name,
                'outputFormat': 'application/json',
                'srsName': coordinate_system,
                'count': sample_size
            }
            
            # FIXED: Add spatial filter if location provided
            if location_center:
                bbox = self._create_sample_bbox_fixed(location_center, coordinate_system)
                if bbox:
                    params['bbox'] = f"{bbox},{coordinate_system}"
                    print(f"   📍 Using spatial filter: {bbox}")
                else:
                    print(f"   ⚠️ Could not create spatial filter, using service default area")
            
            response = requests.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            print(f"   ✅ Retrieved {len(features)} sample features")
            
            if not features:
                return {
                    "error": "No sample data available",
                    "features_found": 0,
                    "sample_success": False
                }
            
            # Comprehensive attribute analysis
            return self._perform_comprehensive_attribute_analysis(features, config)
            
        except Exception as e:
            print(f"   ❌ Sample analysis error: {e}")
            return {
                "error": f"Could not analyze sample data: {str(e)}",
                "sample_success": False
            }
    
    def _create_sample_bbox_fixed(self, location_center: Union[List[float], Dict], coordinate_system: str) -> Optional[str]:
        """FIXED: Create bounding box with proper coordinate handling."""
        try:
            # Extract coordinates from different input formats
            if isinstance(location_center, dict):
                if 'lat' in location_center and 'lon' in location_center:
                    lat, lon = float(location_center['lat']), float(location_center['lon'])
                else:
                    print(f"   ❌ Invalid location_center dict format: {location_center}")
                    return None
            elif isinstance(location_center, (list, tuple)) and len(location_center) == 2:
                lat, lon = float(location_center[0]), float(location_center[1])
            else:
                print(f"   ❌ Invalid location_center format: {location_center}")
                return None
            
            print(f"   📍 Processing coordinates: lat={lat}, lon={lon}")
            
            if coordinate_system == "EPSG:4326":
                # WGS84 - use degrees (approximately 10km radius)
                buffer = 0.1
                bbox = f"{lon-buffer},{lat-buffer},{lon+buffer},{lat+buffer}"
                print(f"   🌐 WGS84 bbox created: {bbox}")
                return bbox
            
            elif coordinate_system == "EPSG:28992":
                # RD New - convert coordinates
                try:
                    import pyproj
                    print(f"   🔄 Converting WGS84 to RD New...")
                    
                    # FIXED: Ensure inputs are scalar values
                    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
                    x, y = transformer.transform(float(lon), float(lat))
                    
                    print(f"   📍 RD New coordinates: x={x:.2f}, y={y:.2f}")
                    
                    buffer = 10000  # 10km in meters
                    bbox = f"{x-buffer},{y-buffer},{x+buffer},{y+buffer}"
                    print(f"   🗺️ RD New bbox created: {bbox}")
                    return bbox
                    
                except ImportError:
                    print("   ⚠️ PyProj not available for coordinate transformation")
                    return None
                except Exception as e:
                    print(f"   ❌ Coordinate transformation error: {e}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"   ❌ Error creating bbox: {e}")
            return None
    
    def _perform_comprehensive_attribute_analysis(self, features: List[Dict], config: Dict) -> Dict:
        """FIXED: Perform comprehensive analysis with better error handling."""
        try:
            analysis_focus = config.get("analysis_focus", "")
            
            # Initialize analysis structure
            attribute_analysis = {}
            classification_fields = []
            numeric_fields = []
            area_fields = []
            
            print(f"   🔍 Analyzing {len(features)} features for {analysis_focus}")
            
            # Analyze each feature
            for feature in features:
                properties = feature.get('properties', {})
                
                for attr_name, attr_value in properties.items():
                    if attr_name not in attribute_analysis:
                        attribute_analysis[attr_name] = {
                            "type": type(attr_value).__name__,
                            "values": set(),
                            "non_null_count": 0,
                            "sample_values": [],
                            "is_classification": False,
                            "is_area": False
                        }
                    
                    if attr_value is not None and attr_value != '':
                        str_value = str(attr_value)
                        attribute_analysis[attr_name]["values"].add(str_value)
                        attribute_analysis[attr_name]["non_null_count"] += 1
            
            # Process analysis results
            for attr_name, analysis in attribute_analysis.items():
                values_list = list(analysis["values"])
                analysis["unique_count"] = len(values_list)
                analysis["sample_values"] = values_list[:10]  # Keep first 10 as examples
                
                # Classify attribute types
                attr_lower = attr_name.lower()
                
                # Check if numeric/area field
                if analysis["type"] in ["int", "float"] or self._is_numeric_field(values_list):
                    numeric_fields.append(attr_name)
                    
                    # Check if area field
                    if any(keyword in attr_lower for keyword in ['oppervlakte', 'grootte', 'area', 'shape_area']):
                        analysis["is_area"] = True
                        area_fields.append(attr_name)
                
                # Check if classification field
                if (analysis["unique_count"] < 50 and analysis["unique_count"] > 1 and
                    any(keyword in attr_lower for keyword in ['bodemgebruik', 'categorie', 'klasse', 'type', 'status'])):
                    analysis["is_classification"] = True
                    classification_fields.append(attr_name)
                    
                    # FIXED: Analyze classification values for land use
                    if analysis_focus == "land_use_classification":
                        analysis["agricultural_values"] = self._find_agricultural_values(values_list)
                        analysis["urban_values"] = self._find_urban_values(values_list)
                        analysis["natural_values"] = self._find_natural_values(values_list)
                        
                        print(f"   🌾 {attr_name} agricultural values: {analysis['agricultural_values']}")
                        print(f"   🏙️ {attr_name} urban values: {analysis['urban_values']}")
                    
                    # Analyze for building status
                    elif analysis_focus == "building_characteristics":
                        analysis["active_values"] = self._find_active_building_values(values_list)
                        print(f"   🏠 {attr_name} active values: {analysis['active_values']}")
                
                # Remove large values set to save memory
                del analysis["values"]
            
            print(f"   📊 Analysis complete: {len(classification_fields)} classification fields found")
            if classification_fields:
                print(f"   🏷️ Classification fields: {classification_fields}")
            
            return {
                "features_analyzed": len(features),
                "total_attributes": len(attribute_analysis),
                "attribute_details": attribute_analysis,
                "classification_fields": classification_fields,
                "numeric_fields": numeric_fields,
                "area_fields": area_fields,
                "sample_success": True,
                "analysis_focus": analysis_focus
            }
            
        except Exception as e:
            print(f"   ❌ Attribute analysis error: {e}")
            return {
                "error": f"Attribute analysis failed: {str(e)}",
                "sample_success": False
            }
    
    def _find_agricultural_values(self, values: List[str]) -> List[str]:
        """Find values that represent agricultural land use."""
        agricultural_terms = ['agrarisch', 'landbouw', 'akkerbouw', 'veeteelt', 'grasland', 'weide']
        return [v for v in values if any(term in v.lower() for term in agricultural_terms)]
    
    def _find_urban_values(self, values: List[str]) -> List[str]:
        """Find values that represent urban/built-up land use."""
        urban_terms = ['bebouwd', 'stedelijk', 'urban', 'woongebied', 'industrie', 'wonen']
        return [v for v in values if any(term in v.lower() for term in urban_terms)]
    
    def _find_natural_values(self, values: List[str]) -> List[str]:
        """Find values that represent natural land use."""
        natural_terms = ['bos', 'natuur', 'water', 'natuurlijk', 'recreatie']
        return [v for v in values if any(term in v.lower() for term in natural_terms)]
    
    def _find_active_building_values(self, values: List[str]) -> List[str]:
        """Find values that represent active/in-use buildings."""
        active_terms = ['gebruik', 'actief', 'in gebruik', 'operationeel']
        return [v for v in values if any(term in v.lower() for term in active_terms)]
    
    def _is_numeric_field(self, values: List[str]) -> bool:
        """Check if string values are actually numeric."""
        try:
            numeric_count = 0
            for value in values[:5]:  # Check first 5 values
                try:
                    float(value)
                    numeric_count += 1
                except (ValueError, TypeError):
                    pass
            return numeric_count >= 3  # Majority numeric
        except:
            return False
    
    def _generate_filter_recommendations(self, config: Dict, sample_analysis: Dict, capabilities: Dict) -> Dict:
        """Generate intelligent filter recommendations."""
        recommendations = {
            "primary_classification_field": None,
            "recommended_filters": {},
            "agricultural_filter": None,
            "urban_filter": None,
            "sample_based_guidance": {}
        }
        
        if not sample_analysis.get("sample_success"):
            recommendations["note"] = "No sample analysis available - filters based on schema only"
            return recommendations
        
        analysis_focus = config.get("analysis_focus", "")
        attribute_details = sample_analysis.get("attribute_details", {})
        classification_fields = sample_analysis.get("classification_fields", [])
        
        # Find primary classification field
        if classification_fields:
            # For land use, prioritize 'bodemgebruik' or 'categorie'
            if analysis_focus == "land_use_classification":
                for field in ['bodemgebruik', 'categorie']:
                    if field in classification_fields:
                        recommendations["primary_classification_field"] = field
                        break
                if not recommendations["primary_classification_field"]:
                    recommendations["primary_classification_field"] = classification_fields[0]
            else:
                recommendations["primary_classification_field"] = classification_fields[0]
        
        # Generate specific filter recommendations
        primary_field = recommendations["primary_classification_field"]
        if primary_field and primary_field in attribute_details:
            field_analysis = attribute_details[primary_field]
            
            # FIXED: Create filters using discovered values
            if analysis_focus == "land_use_classification":
                agricultural_values = field_analysis.get("agricultural_values", [])
                if agricultural_values:
                    recommendations["agricultural_filter"] = self._create_filter_expression(primary_field, agricultural_values)
                    recommendations["recommended_filters"]["agricultural_land"] = {
                        "field": primary_field,
                        "values": agricultural_values,
                        "filter": recommendations["agricultural_filter"],
                        "description": f"Filter for agricultural land using discovered values"
                    }
                
                urban_values = field_analysis.get("urban_values", [])
                if urban_values:
                    recommendations["urban_filter"] = self._create_filter_expression(primary_field, urban_values)
                    recommendations["recommended_filters"]["urban_areas"] = {
                        "field": primary_field,
                        "values": urban_values,
                        "filter": recommendations["urban_filter"],
                        "description": f"Filter for urban areas using discovered values"
                    }
            
            # Add guidance for available values
            all_values = field_analysis.get("sample_values", [])
            if all_values:
                recommendations["sample_based_guidance"][primary_field] = {
                    "available_values": all_values[:10],
                    "usage": f"Use {primary_field} = 'value' with one of the available values",
                    "total_unique_values": field_analysis.get("unique_count", 0)
                }
        
        return recommendations
    
    def _create_filter_expression(self, field_name: str, values: List[str]) -> str:
        """Create appropriate filter expression for field and values."""
        if len(values) == 1:
            return f"{field_name} = '{values[0]}'"
        elif len(values) <= 5:
            value_list = "','".join(values)
            return f"{field_name} IN ('{value_list}')"
        else:
            # Too many values, use first few
            value_list = "','".join(values[:3])
            return f"{field_name} IN ('{value_list}') /* and {len(values)-3} more values */"
    
    def _is_primary_layer(self, layer_name: str) -> bool:
        """Check if this is a primary layer we should get attributes for."""
        primary_layers = [
            "bestand_bodemgebruik_2015",
            "bag:pand",
            "kadastralekaart:Perceel", 
            "natura2000:natura2000",
            "cbs_gemeente"
        ]
        
        return any(primary in layer_name for primary in primary_layers)
    
    def _get_layer_attributes(self, service_url: str, layer_name: str) -> Dict:
        """Get detailed attributes for a specific layer."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'DescribeFeatureType',
                'typeName': layer_name
            }
            
            response = requests.get(service_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse schema
            root = ET.fromstring(response.content)
            
            attributes = {}
            
            # Extract attribute information from schema
            for element in root.iter():
                if element.tag.endswith('element'):
                    attr_name = element.get('name')
                    attr_type = element.get('type', 'unknown')
                    
                    if attr_name and not attr_name.lower() in ['geometry', 'geom']:
                        attributes[attr_name] = {
                            "type": attr_type,
                            "filterable": True
                        }
            
            return {
                "count": len(attributes),
                "details": attributes,
                "discovery_method": "DescribeFeatureType"
            }
            
        except Exception as e:
            print(f"    ⚠️ Could not get attributes for {layer_name}: {e}")
            return {"error": f"Could not get attributes: {str(e)}"}


# Quick test function
def test_fixed_discovery():
    """Test the fixed discovery tool."""
    discovery_tool = IntentDrivenPDOKDiscoveryTool()
    
    print("🧪 Testing FIXED Discovery Tool")
    print("=" * 50)
    
    # Test land use discovery with sampling
    result = discovery_tool.forward(
        service_name="bestandbodemgebruik",
        get_attributes=True,
        sample_data=True,
        location_center=[52.0887, 5.0953],  # Utrecht
        sample_size=15
    )
    
    if result.get("discovery_success"):
        print("✅ Discovery successful!")
        
        sample_analysis = result.get("sample_analysis", {})
        if sample_analysis.get("sample_success"):
            print(f"📊 Analyzed {sample_analysis['features_analyzed']} features")
            
            # Show discovered values for classification fields
            attr_details = sample_analysis.get("attribute_details", {})
            for field in sample_analysis.get("classification_fields", []):
                if field in attr_details:
                    field_data = attr_details[field]
                    print(f"🏷️ Field '{field}':")
                    print(f"   Sample values: {field_data.get('sample_values', [])[:5]}")
                    print(f"   Agricultural: {field_data.get('agricultural_values', [])}")
                    print(f"   Urban: {field_data.get('urban_values', [])}")
        
        # Show filter recommendations
        recommendations = result.get("filter_recommendations", {})
        if recommendations.get("agricultural_filter"):
            print(f"🌾 Recommended agricultural filter: {recommendations['agricultural_filter']}")
        if recommendations.get("urban_filter"):
            print(f"🏙️ Recommended urban filter: {recommendations['urban_filter']}")
    
    else:
        print(f"❌ Discovery failed: {result.get('error')}")

if __name__ == "__main__":
    test_fixed_discovery()