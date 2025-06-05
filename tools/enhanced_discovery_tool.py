# tools/enhanced_discovery_tool.py

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from smolagents import Tool
import math
from typing import Dict, List, Optional, Union, Tuple

class IntentDrivenPDOKDiscoveryTool(Tool):
    """
    Intent-driven PDOK service discovery that focuses on specific services based on user needs.
    Instead of discovering all services, this tool targets specific services based on analysis intent.
    """
    
    name = "discover_pdok_services"
    description = """Discover specific PDOK WFS services based on analysis intent.

This tool helps the AI understand what specific PDOK service contains the data needed for analysis.
The AI should specify which service to discover based on the user's intent.

Supported services:
- 'bestandbodemgebruik' or 'landuse': Land use classification data (agricultural, urban, etc.)
- 'bag': Buildings and addresses 
- 'cadastral': Cadastral parcels and boundaries
- 'natura2000': Protected nature areas
- 'cbs': Administrative boundaries and statistics
- 'bgt': Detailed topography
- 'wetlands': Protected wetland areas

The tool returns detailed attribute information for targeted analysis."""
    
    inputs = {
        "service_name": {
            "type": "string", 
            "description": "Specific service to discover: 'bestandbodemgebruik', 'bag', 'cadastral', 'natura2000', 'cbs', 'bgt', 'wetlands', or 'all'"
        },
        "get_attributes": {
            "type": "boolean",
            "description": "Whether to get detailed attribute information (default: True)",
            "nullable": True
        }
    }
    output_type = "object"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        
        # Enhanced service definitions with land use service included
        self.services = {
            "bestandbodemgebruik": {
                "name": "CBS - Land Use Database (Bestand Bodemgebruik)",
                "url": "https://service.pdok.nl/cbs/bestandbodemgebruik/2015/wfs/v1_0",
                "description": "Detailed land use classification for the Netherlands from 2015. Comprehensive dataset showing how land is actually used across the country.",
                "typical_use": "Agricultural land analysis, urban planning, environmental studies, land use distribution",
                "keywords": ["land use", "agriculture", "urban planning", "bodemgebruik", "classification"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "bestandbodemgebruik:bestand_bodemgebruik_2015",
                "feature_count": "189,601 polygons",
                "coverage": "Entire Netherlands",
                "key_attributes": {
                    "expected": ["bgb2015_hoofdklasse_code", "bgb2015_hoofdklasse_label", "shape_area"],
                    "description": "Land use classification codes and area measurements"
                }
            },
            "bag": {
                "name": "BAG - Buildings and Addresses",
                "url": "https://service.pdok.nl/lv/bag/wfs/v2_0",
                "description": "Dutch Buildings and Addresses Database",
                "typical_use": "Building analysis, address lookup, construction information",
                "keywords": ["buildings", "addresses", "construction", "bouwjaar"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "bag:pand",
                "key_attributes": {
                    "expected": ["bouwjaar", "oppervlakte", "status"],
                    "description": "Building construction year, area, and status information"
                }
            },
            "cadastral": {
                "name": "Cadastral Map - Kadastrale Kaart v5",
                "url": "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0",
                "description": "Cadastral parcel boundaries and reference information",
                "typical_use": "Parcel visualization, property boundaries, cadastral reference",
                "keywords": ["parcels", "boundaries", "kadaster", "property"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "kadastralekaart:Perceel",
                "key_attributes": {
                    "expected": ["kadastraleGrootteWaarde", "perceelnummer"],
                    "description": "Parcel area in square meters and identification numbers"
                }
            },
            "natura2000": {
                "name": "Natura 2000 - Protected Nature Areas",
                "url": "https://service.pdok.nl/rvo/natura2000/wfs/v1_0",
                "description": "EU protected natural areas network",
                "typical_use": "Environmental protection analysis, conservation planning",
                "keywords": ["protected areas", "nature", "conservation", "environment"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "natura2000:natura2000",
                "key_attributes": {
                    "expected": ["naam", "gebiedsnaam", "type_gebied"],
                    "description": "Protected area names and types"
                }
            },
            "cbs": {
                "name": "CBS - Administrative Boundaries",
                "url": "https://service.pdok.nl/cbs/wijkenbuurten/wfs/v1_0",
                "description": "Administrative boundaries and statistical areas",
                "typical_use": "Municipal analysis, administrative context, demographic studies",
                "keywords": ["boundaries", "municipalities", "statistics", "administrative"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "wijkenbuurten:cbs_gemeente_2023_gegeneraliseerd",
                "key_attributes": {
                    "expected": ["gemeentenaam", "provinciename", "gemeentecode"],
                    "description": "Municipality and province names and codes"
                }
            },
            "bgt": {
                "name": "BGT - Large Scale Topography",
                "url": "https://service.pdok.nl/lv/bgt/wfs/v1_0", 
                "description": "Detailed topographic features",
                "typical_use": "Infrastructure mapping, detailed topographic analysis",
                "keywords": ["topography", "infrastructure", "roads", "water"],
                "coordinate_system": "EPSG:28992",
                "primary_layer": "varies",
                "key_attributes": {
                    "expected": ["varies by layer"],
                    "description": "Depends on specific BGT layer"
                }
            },
            "wetlands": {
                "name": "Wetlands - Ramsar Protected Wetlands",
                "url": "https://service.pdok.nl/rvo/beschermdegebieden/wetlands/wfs/v1_0",
                "description": "Protected wetland areas under Ramsar Convention",
                "typical_use": "Wetland protection analysis, water management",
                "keywords": ["wetlands", "water", "protection", "ramsar"],
                "coordinate_system": "EPSG:28992", 
                "primary_layer": "beschermdegebieden:protectedsite",
                "key_attributes": {
                    "expected": ["naam", "type_bescherming"],
                    "description": "Wetland names and protection types"
                }
            }
        }
    
    def forward(self, service_name: str, get_attributes: Optional[bool] = True) -> Dict:
        """Discover specific PDOK service based on intent."""
        try:
            print(f"🎯 Intent-driven PDOK discovery: {service_name}")
            
            # Handle aliases for land use service
            if service_name in ["landuse", "land_use", "bodemgebruik"]:
                service_name = "bestandbodemgebruik"
            
            if service_name == "all":
                return self._discover_all_services(get_attributes)
            elif service_name in self.services:
                return self._discover_single_service(service_name, get_attributes)
            else:
                available_services = list(self.services.keys())
                return {
                    "error": f"Unknown service: {service_name}. Available services: {available_services}",
                    "available_services": available_services,
                    "service_mapping": {
                        "land_use_analysis": "bestandbodemgebruik",
                        "building_analysis": "bag", 
                        "parcel_analysis": "cadastral",
                        "environmental_analysis": "natura2000",
                        "boundary_analysis": "cbs"
                    }
                }
                
        except Exception as e:
            return {"error": f"Service discovery error: {str(e)}"}
    
    def _discover_single_service(self, service_name: str, get_attributes: bool) -> Dict:
        """Discover a single specific service."""
        config = self.services[service_name]
        
        print(f"📡 Discovering {service_name}: {config['name']}")
        
        capabilities = self._get_service_capabilities(config["url"], get_attributes)
        
        result = {
            "service": {
                **config,
                "capabilities": capabilities,
                "available": not capabilities.get('error'),
                "layers": capabilities.get('layers', [])
            },
            "targeted_discovery": True,
            "intent_guidance": self._get_intent_guidance(service_name),
            "attribute_guidance": self._get_attribute_guidance(service_name, capabilities)
        }
        
        return result
    
    def _discover_all_services(self, get_attributes: bool) -> Dict:
        """Discover all services (only when explicitly requested)."""
        print("⚠️ Discovering ALL services - consider targeting specific service for better performance")
        
        discovered_services = {}
        
        for key, config in self.services.items():
            print(f"📡 Checking {key}...")
            capabilities = self._get_service_capabilities(config["url"], get_attributes)
            
            discovered_services[key] = {
                **config,
                "capabilities": capabilities,
                "available": not capabilities.get('error'),
                "layers": capabilities.get('layers', [])
            }
        
        return {
            "services": discovered_services,
            "summary": f"Discovered {len(discovered_services)} PDOK services",
            "recommendation": "Use targeted discovery for better performance - specify service_name",
            "service_selection_guide": {
                "land_use_analysis": "bestandbodemgebruik",
                "agricultural_analysis": "bestandbodemgebruik", 
                "building_analysis": "bag",
                "parcel_analysis": "cadastral",
                "environmental_analysis": "natura2000 or wetlands",
                "administrative_analysis": "cbs"
            }
        }
    
    def _get_service_capabilities(self, service_url: str, get_attributes: bool) -> Dict:
        """Get capabilities and optionally attributes for a service."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            print(f"  Requesting capabilities from: {service_url}")
            response = requests.get(service_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Parse XML to extract layer info
            root = ET.fromstring(response.content)
            
            layers = []
            for feature_type in root.iter():
                if feature_type.tag.endswith('FeatureType'):
                    name_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Name')
                    title_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Title')
                    abstract_elem = feature_type.find('.//{http://www.opengis.net/wfs/2.0}Abstract')
                    
                    if name_elem is not None:
                        layer_info = {
                            "name": name_elem.text,
                            "title": title_elem.text if title_elem is not None else name_elem.text,
                            "description": abstract_elem.text if abstract_elem is not None else ""
                        }
                        
                        # Get attributes if requested and for primary layers
                        if get_attributes and self._is_primary_layer(name_elem.text, service_url):
                            print(f"  🔬 Getting attributes for: {name_elem.text}")
                            attributes = self._get_layer_attributes(service_url, name_elem.text)
                            layer_info["attributes"] = attributes
                        
                        layers.append(layer_info)
            
            return {
                "layers": layers,
                "layer_count": len(layers),
                "service_operational": True,
                "attributes_retrieved": get_attributes
            }
            
        except Exception as e:
            error_msg = f"Could not get capabilities: {str(e)}"
            print(f"  ❌ {error_msg}")
            return {"error": error_msg}
    
    def _is_primary_layer(self, layer_name: str, service_url: str) -> bool:
        """Check if this is a primary layer we should get attributes for."""
        primary_layers = [
            "bestand_bodemgebruik_2015",
            "bag:pand",
            "kadastralekaart:Perceel", 
            "natura2000:natura2000",
            "beschermdegebieden:protectedsite"
        ]
        
        return any(primary in layer_name for primary in primary_layers)
    
    def _get_layer_attributes(self, service_url: str, layer_name: str) -> Dict:
        """Get attributes for a specific layer."""
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
                            "filterable": True,
                            "usage": self._generate_attribute_usage(attr_name)
                        }
            
            return {
                "count": len(attributes),
                "details": attributes,
                "discovery_method": "DescribeFeatureType"
            }
            
        except Exception as e:
            print(f"    ⚠️ Could not get attributes for {layer_name}: {e}")
            return {"error": f"Could not get attributes: {str(e)}"}
    
    def _generate_attribute_usage(self, attr_name: str) -> str:
        """Generate usage guidance for attributes."""
        attr_lower = attr_name.lower()
        
        if 'hoofdklasse' in attr_lower:
            return "Primary land use classification - use for filtering by land use type"
        elif 'code' in attr_lower and 'klasse' in attr_lower:
            return "Classification code - use for specific land use category filtering"
        elif 'area' in attr_lower or 'oppervlakte' in attr_lower:
            return "Area measurement - use for size-based filtering (numeric)"
        elif 'grootte' in attr_lower:
            return "Size/area field - use for area-based filtering (numeric)"
        elif 'jaar' in attr_lower or 'year' in attr_lower:
            return "Year field - use for temporal filtering (numeric)"
        elif 'naam' in attr_lower or 'name' in attr_lower:
            return "Name field - use for text-based filtering"
        elif 'type' in attr_lower or 'status' in attr_lower:
            return "Category/status field - use for classification filtering"
        else:
            return "General attribute - check data type for appropriate filtering"
    
    def _get_intent_guidance(self, service_name: str) -> Dict:
        """Provide intent-specific guidance for using the service."""
        guidance = {
            "bestandbodemgebruik": {
                "primary_use": "Land use classification and agricultural analysis",
                "analysis_types": ["Agricultural land distribution", "Urban vs rural analysis", "Land use planning"],
                "common_filters": ["Land use classification codes", "Area thresholds"],
                "next_steps": [
                    "1. Use discovered classification attributes to filter by land use type",
                    "2. Use area attributes to filter by size thresholds",
                    "3. Calculate total areas by classification type"
                ]
            },
            "bag": {
                "primary_use": "Building and address analysis",
                "analysis_types": ["Building age analysis", "Building size distribution", "Address lookup"],
                "common_filters": ["Construction year", "Building area", "Building status"],
                "next_steps": [
                    "1. Use 'bouwjaar' for construction year filtering",
                    "2. Use area attributes for size-based analysis",
                    "3. Filter by building status for active buildings"
                ]
            },
            "cadastral": {
                "primary_use": "Parcel visualization and area analysis",
                "analysis_types": ["Property size analysis", "Parcel boundary visualization"],
                "common_filters": ["Parcel area (kadastraleGrootteWaarde)", "Parcel numbers"],
                "next_steps": [
                    "1. Use 'kadastraleGrootteWaarde' for parcel area filtering",
                    "2. Filter by size thresholds for suitability analysis"
                ]
            }
        }
        
        return guidance.get(service_name, {
            "primary_use": "General spatial analysis",
            "analysis_types": ["Spatial queries", "Feature analysis"],
            "common_filters": ["Area, name, type fields"],
            "next_steps": ["Use discovered attributes for filtering"]
        })
    
    def _get_attribute_guidance(self, service_name: str, capabilities: Dict) -> Dict:
        """Provide specific attribute usage guidance."""
        if capabilities.get('error'):
            return {"note": "No attributes available due to capability error"}
        
        layers = capabilities.get('layers', [])
        attribute_guidance = {}
        
        for layer in layers:
            if 'attributes' in layer and layer['attributes']:
                layer_name = layer['name']
                attributes = layer['attributes'].get('details', {})
                
                layer_guidance = {}
                for attr_name, attr_info in attributes.items():
                    layer_guidance[attr_name] = {
                        "type": attr_info.get('type', 'unknown'),
                        "usage": attr_info.get('usage', 'General attribute'),
                        "example_filter": self._generate_example_filter(attr_name, attr_info.get('type', ''))
                    }
                
                attribute_guidance[layer_name] = layer_guidance
        
        return attribute_guidance
    
    def _generate_example_filter(self, attr_name: str, attr_type: str) -> str:
        """Generate example filter for an attribute."""
        attr_lower = attr_name.lower()
        
        if 'int' in attr_type.lower() or 'double' in attr_type.lower() or 'decimal' in attr_type.lower():
            if 'area' in attr_lower or 'grootte' in attr_lower:
                return f"{attr_name} >= 5000"  # Area example
            elif 'jaar' in attr_lower or 'year' in attr_lower:
                return f"{attr_name} <= 1950"  # Year example
            else:
                return f"{attr_name} > 100"  # General numeric
        else:
            if 'klasse' in attr_lower or 'type' in attr_lower:
                return f"{attr_name} = 'agrarisch'"  # Classification example
            else:
                return f"{attr_name} LIKE '%search_term%'"  # Text example



class CoreToolRegistry:
    """Registry of core tools that should be kept in the project."""
    
    ESSENTIAL_TOOLS = {
        # Discovery and planning
        "enhanced_discovery_tool.py": "Intent-driven PDOK service discovery",
        
        # Data fetching  
        "flexible_ai_driven_spatial_tools.py": "Flexible data fetching and analysis",
        
        # Location services
        "enhanced_pdok_location_tool.py": "Intelligent location search",
        
        # Coordinate conversion
        "coordinate_conversion_tool.py": "WGS84 to RD New conversion",
        
        # Tool initialization
        "__init__.py": "Tool registry and imports"
    }
    
    DEPRECATED_TOOLS = {
        # Old rigid tools that can be removed
        "ai_intelligent_tools.py": "Replaced by enhanced_discovery_tool.py",
        "enhanced_ai_intelligent_tools.py": "Redundant with enhanced_discovery_tool.py", 
        "enhanced_multi_layer_spatial_tool.py": "Complex tool not used by current workflow",
        "kadaster_tool.py": "Old rigid cadastral tool",
        "pdok_building_tool.py": "Old rigid building tool",
        "pdok_intelligent_agent_tool.py": "Old complex agent tool",
        "pdok_modular_tools.py": "Old modular approach",
        "pdok_service_discovery_tool.py": "Old service discovery"
    }
    
    @classmethod
    def get_cleanup_plan(cls):
        """Get plan for cleaning up tools directory."""
        return {
            "keep": list(cls.ESSENTIAL_TOOLS.keys()),
            "remove": list(cls.DEPRECATED_TOOLS.keys()),
            "keep_descriptions": cls.ESSENTIAL_TOOLS,
            "remove_reasons": cls.DEPRECATED_TOOLS
        }