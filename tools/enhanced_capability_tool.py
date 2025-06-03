# tools/enhanced_capability_tool.py - User-friendly capability and example tool

from smolagents import Tool
from typing import Dict, List, Optional

class EnhancedCapabilityTool(Tool):
    """
    Tool that provides user-friendly responses about PDOK capabilities and examples.
    This tool handles capability questions without dumping JSON.
    """
    
    name = "provide_capability_info"
    description = """Provide user-friendly information about PDOK capabilities and examples.
    
    Use this tool when users ask about:
    - What data can they search for
    - What types of queries they can make
    - Examples of searches they can try
    - Available services and their uses
    
    This tool provides conversational responses, not technical JSON dumps."""
    
    inputs = {
        "query_type": {
            "type": "string",
            "description": "Type of capability question: 'overview', 'examples', 'specific_service', 'query_help'"
        },
        "specific_focus": {
            "type": "string", 
            "description": "Specific area of interest if mentioned (buildings, addresses, parcels, etc.)",
            "nullable": True
        }
    }
    output_type = "string"
    is_initialized = True
    
    def __init__(self):
        super().__init__()
        self.capabilities = {
            "buildings": {
                "title": "🏢 Buildings & Properties",
                "description": "Search for buildings, their characteristics, and residential objects",
                "examples": [
                    "Show me buildings near Amsterdam Centraal built before 1950",
                    "Find large buildings (>500m²) in Rotterdam city center", 
                    "Get residential properties on Damrak street in Amsterdam",
                    "Show me buildings with area > 300m² in Utrecht"
                ],
                "filters": ["Construction year", "Building area", "Usage type", "Status"],
                "data_source": "BAG (Buildings and Addresses Database)"
            },
            "addresses": {
                "title": "📍 Addresses & Locations",
                "description": "Find specific addresses, postal codes, and location information",
                "examples": [
                    "Get addresses on Kalverstraat in Amsterdam",
                    "Find all properties with postal code 1012AB",
                    "Show me addresses near Groningen train station",
                    "Get address information for Damrak 1, Amsterdam"
                ],
                "filters": ["Street name", "Postal code", "House number", "Municipality"],
                "data_source": "BAG (Buildings and Addresses Database)"
            },
            "parcels": {
                "title": "🗺️ Land Parcels & Property",
                "description": "Search for land parcels, property boundaries, and ownership information",
                "examples": [
                    "Show me large land parcels near Utrecht University",
                    "Find property boundaries in Amsterdam city center",
                    "Get parcels with area > 1000m² in Groningen",
                    "Show me agricultural land near Almere"
                ],
                "filters": ["Parcel area", "Land use type", "Ownership status"],
                "data_source": "BRK (Cadastral Registry)"
            },
            "topography": {
                "title": "🌍 Geographic Features",
                "description": "Access detailed topographic and geographic information",
                "examples": [
                    "Show me water features near Rotterdam",
                    "Get road networks in Amsterdam",
                    "Find green spaces in Utrecht city center",
                    "Show me building footprints in Groningen"
                ],
                "filters": ["Feature type", "Area size", "Administrative region"],
                "data_source": "BGT (Large-scale Topography)"
            },
            "administrative": {
                "title": "🏛️ Administrative Areas",
                "description": "Search for municipal boundaries, districts, and statistical areas",
                "examples": [
                    "Show me municipality boundaries around Utrecht",
                    "Get district boundaries in Amsterdam",
                    "Find neighborhood areas in Rotterdam",
                    "Show me provincial boundaries in the north"
                ],
                "filters": ["Administrative level", "Population size", "Area size"],
                "data_source": "CBS (Statistics Netherlands)"
            }
        }
    
    def forward(self, query_type: str, specific_focus: Optional[str] = None) -> str:
        """Provide user-friendly capability information."""
        
        if query_type == "overview":
            return self._provide_overview()
        elif query_type == "examples": 
            return self._provide_examples()
        elif query_type == "specific_service" and specific_focus:
            return self._provide_specific_info(specific_focus)
        elif query_type == "query_help":
            return self._provide_query_help()
        else:
            return self._provide_overview()
    
    def _provide_overview(self) -> str:
        """Provide comprehensive overview of capabilities."""
        response = """# 🗂️ Available Data Sources & Search Capabilities

You can search for various types of Dutch geographic data through PDOK services:

"""
        
        for key, info in self.capabilities.items():
            response += f"## {info['title']}\n"
            response += f"{info['description']}\n"
            response += f"*Source: {info['data_source']}*\n\n"
            
            response += "**Available filters:**\n"
            for filter_type in info['filters']:
                response += f"- {filter_type}\n"
            response += "\n"
        
        response += """## 💡 Ready-to-Try Examples

**🏛️ Historic Search**: "Show me buildings near Amsterdam Centraal built before 1920"

**📏 Size Search**: "Find large buildings (>1000m²) in Rotterdam city center"

**🏘️ Street Search**: "Get all properties on Damrak street in Amsterdam"

**🌍 Area Search**: "Show me land parcels with area > 5000m² near Utrecht"

---

**🚀 Want to try something?** 
- Say "run examples" to see more detailed examples
- Ask "how do I search for [specific thing]?" for targeted help
- Or just try any of the examples above!

What type of data interests you most?"""

        return response
    
    def _provide_examples(self) -> str:
        """Provide detailed query examples."""
        response = """# 🔍 Ready-to-Run Query Examples

Just copy any of these into the chat, or say "run example [number]":

"""
        
        example_counter = 1
        for category, info in self.capabilities.items():
            response += f"## {info['title']}\n\n"
            
            for example in info['examples']:
                response += f"**Example {example_counter}: {example.split(' ', 2)[2] if len(example.split()) > 2 else 'Search'}**\n"
                response += f"```\n{example}\n```\n"
                response += f"*Searches: {info['description']}*\n\n"
                example_counter += 1
        
        response += """---

**🚀 Want to try one?** Just say:
- "Run example 1" 
- "Show me example 5"
- Or copy any query above directly

**🎯 Need something specific?** Ask:
- "How do I search for buildings by year?"
- "Show me address search examples"
- "What land parcel data can I get?"

Which example interests you most, or what specific type of search do you need help with?"""

        return response
    
    def _provide_specific_info(self, focus: str) -> str:
        """Provide specific information for a data type."""
        focus_lower = focus.lower()
        
        # Map user terms to our categories
        category_mapping = {
            'building': 'buildings', 'buildings': 'buildings', 'pand': 'buildings',
            'address': 'addresses', 'addresses': 'addresses', 'location': 'addresses',
            'parcel': 'parcels', 'parcels': 'parcels', 'land': 'parcels', 'property': 'parcels',
            'topography': 'topography', 'geographic': 'topography', 'features': 'topography',
            'administrative': 'administrative', 'boundaries': 'administrative', 'municipal': 'administrative'
        }
        
        category = None
        for term, cat in category_mapping.items():
            if term in focus_lower:
                category = cat
                break
        
        if not category:
            return self._provide_overview()
        
        info = self.capabilities[category]
        
        response = f"""# {info['title']} - Detailed Information

## 📋 What You Can Search For
{info['description']}

**Data Source**: {info['data_source']}

## 🔍 Available Search Filters
"""
        
        for filter_type in info['filters']:
            response += f"- **{filter_type}**: Use to narrow down results\n"
        
        response += f"\n## 💡 Example Searches\n\n"
        
        for i, example in enumerate(info['examples'], 1):
            response += f"**{i}. {example}**\n"
            # Add explanation for each example
            if 'year' in example.lower() or 'built' in example.lower():
                response += "*Filters by construction year and location*\n\n"
            elif 'area' in example.lower() or 'm²' in example:
                response += "*Filters by size/area and location*\n\n"
            elif 'street' in example.lower() or 'road' in example.lower():
                response += "*Filters by specific street or address*\n\n"
            else:
                response += "*Filters by location and basic criteria*\n\n"
        
        response += """## 🚀 Ready to Search?

**To run any example above, just say:**
- "Run the first example"
- "Try the building search"
- Or copy any example directly

**To create your own search, try patterns like:**
- "Show me [type] near [location] with [filter]"
- "Find [type] in [city] [condition]"
- "Get [type] on [street] in [city]"

What would you like to search for?"""

        return response
    
    def _provide_query_help(self) -> str:
        """Provide help for constructing queries."""
        response = """# 🎯 How to Construct Search Queries

## 📝 Query Patterns That Work

### Basic Pattern:
```
Show me [WHAT] near [WHERE]
```
**Example**: "Show me buildings near Amsterdam Centraal"

### With Filters:
```
Find [WHAT] in [WHERE] with [CONDITION]
```
**Example**: "Find buildings in Rotterdam with area > 500m²"

### Time-based:
```
Show me [WHAT] near [WHERE] built [WHEN]
```
**Example**: "Show me buildings near Utrecht built before 1950"

### Street-specific:
```
Get [WHAT] on [STREET] in [CITY]
```
**Example**: "Get addresses on Damrak street in Amsterdam"

## 🏗️ What You Can Search For

| **Type** | **Keywords** | **Example** |
|----------|-------------|-------------|
| Buildings | buildings, pand, properties | "buildings near station" |
| Addresses | addresses, properties, locations | "addresses on street X" |
| Land Parcels | parcels, land, property boundaries | "large parcels near city" |
| Geographic Features | water, roads, green spaces | "water features in area" |

## 🔧 Useful Filters

| **Filter Type** | **How to Use** | **Example** |
|-----------------|----------------|-------------|
| **Area/Size** | "with area > 300m²", "larger than 500m²" | "buildings with area > 300m²" |
| **Year** | "built before 1950", "constructed after 2000" | "built before 1950" |
| **Location** | "near [landmark]", "in [city]", "around [address]" | "near Amsterdam Centraal" |
| **Street** | "on [street name]", "along [road]" | "on Damrak street" |

## ✅ Ready-to-Use Templates

**🏢 For Buildings:**
```
Show me buildings near [LOCATION] with area > [SIZE]m²
Find buildings in [CITY] built before [YEAR]
Get buildings on [STREET] in [CITY]
```

**📍 For Addresses:**
```
Get addresses on [STREET] in [CITY]
Find properties with postal code [CODE]
Show me addresses near [LANDMARK]
```

**🗺️ For Land Parcels:**
```
Show me land parcels near [LOCATION] with area > [SIZE]m²
Find large parcels in [AREA]
Get property boundaries around [LANDMARK]
```

## 🚀 Try These Now!

1. **"Show me buildings near Groningen train station built before 1950"**
2. **"Find large buildings (>1000m²) in Amsterdam city center"**
3. **"Get addresses on Kalverstraat in Amsterdam"**

Just copy any of these, or use the patterns above to create your own search!

What type of search would you like to try?"""

        return response


class QueryExampleGeneratorTool(Tool):
    """
    Tool that generates specific query examples for different PDOK endpoints.
    Provides concrete examples that users can run immediately.
    """
    
    name = "generate_query_examples"
    description = """Generate concrete query examples for PDOK endpoints.
    
    Use this when users ask for:
    - Examples they can test
    - Specific queries for certain data types
    - Ready-to-run search examples
    - Template queries for different scenarios"""
    
    inputs = {
        "data_type": {
            "type": "string",
            "description": "Type of data: 'buildings', 'addresses', 'parcels', 'all'"
        },
        "include_advanced": {
            "type": "boolean",
            "description": "Include advanced filtering examples",
            "nullable": True
        }
    }
    output_type = "string"
    is_initialized = True
    
    def forward(self, data_type: str, include_advanced: Optional[bool] = False) -> str:
        """Generate query examples."""
        
        if data_type == "all":
            return self._generate_comprehensive_examples(include_advanced)
        elif data_type == "buildings":
            return self._generate_building_examples(include_advanced)
        elif data_type == "addresses":
            return self._generate_address_examples(include_advanced)
        elif data_type == "parcels":
            return self._generate_parcel_examples(include_advanced)
        else:
            return self._generate_comprehensive_examples(include_advanced)
    
    def _generate_comprehensive_examples(self, include_advanced: bool) -> str:
        """Generate comprehensive examples across all data types."""
        response = """# 🔍 Complete Query Examples Collection

        Ready-to-run examples for all PDOK data types. Just copy and paste!

        ## 🏢 Building Searches

        ### Basic Building Queries
        ```
        Show me buildings near Amsterdam Centraal station
        ```
        *Finds: All buildings within 1km of Amsterdam Central Station*

        ```
        Find buildings in Rotterdam city center
        ```
        *Finds: Buildings in Rotterdam's central area*

        ### Filtered Building Queries
        ```
        Show me buildings near Utrecht with area > 500m²
        ```
        *Finds: Large buildings (>500m²) near Utrecht*

        ```
        Find buildings in Groningen built before 1950
        ```
        *Finds: Historic buildings in Groningen (pre-1950)*

        ```
        Get buildings on Damrak street in Amsterdam with area > 200m²
        ```
        *Finds: Buildings on specific street with size filter*

        ## 📍 Address Searches

        ### Basic Address Queries
        ```
        Get addresses on Kalverstraat in Amsterdam
        ```
        *Finds: All addresses on Amsterdam's Kalverstraat*

        ```
        Find addresses near Groningen train station
        ```
        *Finds: Addresses within walking distance of station*

        ### Specific Address Queries
        ```
        Show me properties with postal code 1012AB
        ```
        *Finds: All properties in specific postal code area*

        ```
        Get address information for Leonard Springerlaan 37, Groningen
        ```
        *Finds: Specific address details and location*

        ## 🗺️ Land Parcel Searches

        ### Basic Parcel Queries
        ```
        Show me land parcels near Utrecht University
        ```
        *Finds: Property boundaries near university*

        ```
        Find large parcels in Amsterdam with area > 1000m²
        ```
        *Finds: Large land parcels in Amsterdam*

        """
                
                if include_advanced:
                    response += """## 🔧 Advanced Examples

        ### Complex Building Searches
        ```
        Show me residential buildings near Amsterdam Centraal built between 1900 and 1950 with area > 300m²
        ```
        *Combines: Location + year range + area + usage type*

        ```
        Find commercial buildings in Rotterdam city center larger than 1000m² built after 2000
        ```
        *Combines: Usage type + location + size + construction period*

        ### Multi-criteria Searches
        ```
        Get buildings and land parcels near Groningen train station within 500 meters
        ```
        *Searches: Multiple data types in same area*

        ```
        Show me historic buildings (pre-1920) and their land parcels in Amsterdam canal district
        ```
        *Combines: Buildings + parcels + historic filter + specific area*

        ### Comparative Searches
        ```
        Compare building density: show me all buildings in Amsterdam vs Rotterdam city centers
        ```
        *Compares: Building distribution across different cities*

        """
                
                response += """## 🚀 How to Use These Examples

        ### Option 1: Direct Copy
        Just copy any example above and paste it into the chat.

        ### Option 2: Ask to Run
        Say things like:
        - "Run the first building example"
        - "Try the Utrecht address search"
        - "Execute example 3"

        ### Option 3: Customize
        Use the patterns above but change:
        - **Location**: Replace city/street names
        - **Filters**: Change area sizes, years, etc.
        - **Data type**: Switch between buildings/addresses/parcels

        ## 🎯 Most Popular Examples to Try Right Now

        **🏛️ Historic Buildings**: 
        ```
        Show me buildings near Amsterdam Centraal built before 1920
        ```

        **📏 Large Buildings**: 
        ```
        Find buildings in Rotterdam with area > 1000m²
        ```

        **🏘️ Street Search**: 
        ```
        Get addresses on Damrak street in Amsterdam
        ```

        **🌍 Land Parcels**: 
        ```
        Show me large land parcels near Utrecht University
        ```

        ---

        **Ready to search?** Pick any example above, or ask me to "run example X" and I'll execute it for you!

        Which type of search interests you most?"""

                return response
            
            def _generate_building_examples(self, include_advanced: bool) -> str:
                """Generate building-specific examples."""
                response = """# 🏢 Building Search Examples

        Comprehensive examples for searching Dutch building data (BAG database).

        ## 🏗️ Basic Building Searches

        ```
        Show me buildings near Amsterdam Centraal
        ```
        *Finds: All buildings within 1km of Amsterdam Central Station*

        ```
        Find buildings in Utrecht city center
        ```
        *Finds: Buildings in Utrecht's central district*

        ```
        Get buildings near Groningen train station
        ```
        *Finds: Buildings within walking distance of Groningen station*

        ## 📏 Size-Based Building Searches

        ```
        Show me buildings with area > 500m² in Rotterdam
        ```
        *Finds: Large buildings (>500m²) in Rotterdam*

        ```
        Find small buildings (<200m²) near Amsterdam
        ```
        *Finds: Smaller buildings in Amsterdam area*

        ```
        Get buildings between 300m² and 1000m² in Utrecht
        ```
        *Finds: Medium-sized buildings within area range*

        ## 🏛️ Historic Building Searches

        ```
        Show me buildings built before 1900 in Amsterdam
        ```
        *Finds: Historic buildings (pre-1900) in Amsterdam*

        ```
        Find buildings from 1920-1950 near Rotterdam
        ```
        *Finds: Interwar period buildings near Rotterdam*

        ```
        Get modern buildings (built after 2000) in Groningen
        ```
        *Finds: Contemporary buildings in Groningen*

        ## 🏘️ Street-Specific Building Searches

        ```
        Show me buildings on Damrak street in Amsterdam
        ```
        *Finds: All buildings on Amsterdam's Damrak*

        ```
        Get buildings along Kalverstraat in Amsterdam
        ```
        *Finds: Buildings on Amsterdam's shopping street*

        ```
        Find buildings on Leonard Springerlaan in Groningen
        ```
        *Finds: Buildings on specific Groningen street*

        """

                if include_advanced:
                    response += """## 🔧 Advanced Building Searches

        ### Multi-Criteria Searches
        ```
        Show me large residential buildings (>400m²) built before 1950 near Amsterdam Centraal
        ```
        *Combines: Size + usage + age + location*

        ```
        Find commercial buildings larger than 1000m² in Rotterdam built after 1990
        ```
        *Combines: Usage type + size + construction period + location*

        ### Comparative Searches
        ```
        Compare building ages: show me buildings in Amsterdam vs Utrecht built before 1920
        ```
        *Compares: Historic buildings across different cities*

        ```
        Show me the largest buildings (>2000m²) in each major Dutch city
        ```
        *Finds: Exceptional buildings across multiple locations*

        ### Status and Usage Searches
        ```
        Find active residential buildings with area > 300m² near Utrecht University
        ```
        *Combines: Status + usage + size + landmark location*

        ```
        Show me buildings under construction or recently completed in Amsterdam
        ```
        *Finds: New developments and construction projects*

        """
                
                response += """## 🎯 Ready-to-Test Building Examples

        **🚀 Quick Tests** (copy and paste):

        1. **"Show me buildings near Groningen train station built before 1950"**
        2. **"Find large buildings (>800m²) in Amsterdam city center"**
        3. **"Get buildings on Kalverstraat in Amsterdam"**
        4. **"Show me modern buildings (after 2000) near Utrecht University"**

        ## 🔧 Customization Tips

        **Change Location**: Replace with any Dutch city, address, or landmark
        - Amsterdam → Rotterdam, Utrecht, Groningen, etc.
        - Train station → University, city center, specific address

        **Adjust Filters**:
        - Area: Change 500m² to any size (100m², 1000m², etc.)
        - Year: Use before/after dates (before 1900, after 2010, etc.)
        - Street: Use any Dutch street name

        **Example Customization**:
        Original: "Show me buildings near Amsterdam Centraal built before 1950"
        Custom: "Show me buildings near Rotterdam Centraal built before 1920"

        ---

        **Ready to search?** Pick any example above or ask me to "run building example 1" and I'll execute it for you!

        What type of building search interests you most?"""

                return response
            
            def _generate_address_examples(self, include_advanced: bool) -> str:
                """Generate address-specific examples.""" 
                response = """# 📍 Address Search Examples

        Complete examples for searching Dutch address data (BAG database).

        ## 🏠 Basic Address Searches

        ```
        Get addresses on Damrak street in Amsterdam
        ```
        *Finds: All addresses on Amsterdam's Damrak*

        ```
        Find addresses near Amsterdam Centraal station
        ```
        *Finds: Addresses within walking distance of station*

        ```
        Show me addresses in Utrecht city center
        ```
        *Finds: Addresses in Utrecht's central area*

        ## 📮 Postal Code Searches

        ```
        Show me properties with postal code 1012AB
        ```
        *Finds: All properties in Amsterdam city center postal code*

        ```
        Find addresses in postal code area 9711
        ```
        *Finds: Addresses in Groningen center area (all variants: 9711AB, 9711AC, etc.)*

        ```
        Get address details for postal code 3511AB in Utrecht
        ```
        *Finds: Specific Utrecht city center addresses*

        ## 🏘️ Street-Specific Searches

        ```
        Get all addresses on Kalverstraat in Amsterdam
        ```
        *Finds: Complete address list for shopping street*

        ```
        Find addresses on Leonard Springerlaan in Groningen
        ```
        *Finds: All addresses on specific Groningen street*

        ```
        Show me addresses along Oudegracht in Utrecht
        ```
        *Finds: Addresses on Utrecht's historic canal*

        ## 🎯 Landmark-Based Searches

        ```
        Find addresses near Groningen University
        ```
        *Finds: Addresses within university area*

        ```
        Get addresses around Rotterdam Central Station
        ```
        *Finds: Addresses in station district*

        ```
        Show me addresses near Amsterdam Museum Quarter
        ```
        *Finds: Addresses in cultural district*

        """

                if include_advanced:
                    response += """## 🔧 Advanced Address Searches

        ### House Number Ranges
        ```
        Get addresses 1-50 on Damrak street in Amsterdam
        ```
        *Finds: Specific house number range on street*

        ```
        Find even-numbered addresses on Kalverstraat in Amsterdam
        ```
        *Finds: Addresses with even house numbers only*

        ### Multi-Street Searches
        ```
        Show me addresses on Damrak, Kalverstraat, and Rokin in Amsterdam
        ```
        *Finds: Addresses across multiple streets in same area*

        ### Residential vs Commercial
        ```
        Find residential addresses on Prinsengracht in Amsterdam
        ```
        *Finds: Only residential properties on canal*

        ```
        Get commercial addresses in Rotterdam city center
        ```
        *Finds: Business addresses in central Rotterdam*

        ### Complete Address Verification
        ```
        Verify address: Damrak 1, 1012LG Amsterdam
        ```
        *Verifies: Complete address with postal code*

        ```
        Find exact location of Leonard Springerlaan 37, Groningen
        ```
        *Locates: Specific address with coordinates*

        """
                
                response += """## 🎯 Ready-to-Test Address Examples

        **🚀 Quick Tests** (copy and paste):

        1. **"Get addresses on Damrak street in Amsterdam"**
        2. **"Find addresses near Groningen train station"**
        3. **"Show me properties with postal code 1012AB"**
        4. **"Get address details for Kalverstraat 1 in Amsterdam"**

        ## 🔧 Customization Guide

        **Change Street Names**:
        - Damrak → Any Dutch street (Kalverstraat, Prinsengracht, etc.)
        - Use "straat", "laan", "gracht", "plein" endings

        **Change Cities**:
        - Amsterdam → Rotterdam, Utrecht, Groningen, Den Haag, etc.
        - Include "city center" for central areas

        **Change Postal Codes**:
        - 1012AB (Amsterdam) → 3011 (Rotterdam), 3512 (Utrecht), 9712 (Groningen)
        - Use 4 digits + 2 letters format

        **Example Customizations**:
        - Original: "Get addresses on Damrak in Amsterdam"
        - Custom: "Get addresses on Westerstraat in Groningen"

        ---

        **Ready to search addresses?** Pick any example above or say "run address example 2" and I'll execute it!

        What type of address information do you need?"""

        return response
    
    def _generate_parcel_examples(self, include_advanced: bool) -> str:
        """Generate land parcel examples."""
        response = """# 🗺️ Land Parcel Search Examples

        Examples for searching Dutch cadastral data (BRK database).

        ## 🏞️ Basic Parcel Searches

        ```
        Show me land parcels near Utrecht University
        ```
        *Finds: Property boundaries near university campus*

        ```
        Find large parcels in Amsterdam with area > 1000m²
        ```
        *Finds: Large land parcels in Amsterdam*

        ```
        Get property boundaries around Groningen city center
        ```
        *Finds: Land parcels in central Groningen*

        ## 📏 Size-Based Parcel Searches

        ```
        Show me parcels larger than 5000m² near Rotterdam
        ```
        *Finds: Large land parcels (>5000m²) near Rotterdam*

        ```
        Find small urban parcels (<500m²) in Amsterdam
        ```
        *Finds: Small city parcels in Amsterdam*

        ```
        Get medium-sized parcels (1000-5000m²) in Utrecht area
        ```
        *Finds: Medium parcels within size range*

        ## 🌱 Land Use Searches

        ```
        Show me agricultural parcels near Almere
        ```
        *Finds: Farming land near Almere*

        ```
        Find residential land parcels in Groningen
        ```
        *Finds: Land designated for housing*

        ```
        Get commercial parcels in Rotterdam port area
        ```
        *Finds: Business/industrial land in port*

        ## 🏛️ Historic Parcel Searches

        ```
        Show me historic land parcels in Amsterdam canal district
        ```
        *Finds: Historic property boundaries in old Amsterdam*

        ```
        Find original parcels in Utrecht city center
        ```
        *Finds: Historic land divisions in Utrecht center*

        """

        if include_advanced:
            response += """## 🔧 Advanced Parcel Searches

        ### Ownership and Rights
        ```
        Show me parcels with multiple ownership rights near Amsterdam
        ```
        *Finds: Land with complex ownership structures*

        ```
        Find parcels with building rights in Utrecht development areas
        ```
        *Finds: Land suitable for construction*

        ### Development Potential
        ```
        Get undeveloped parcels larger than 2000m² near major cities
        ```
        *Finds: Land suitable for development*

        ```
        Show me parcels zoned for residential development in Amsterdam region
        ```
        *Finds: Land designated for housing projects*

        ### Comparative Analysis
        ```
        Compare parcel sizes: Amsterdam vs Rotterdam urban areas
        ```
        *Compares: Land parcel patterns across cities*

        ```
        Show me the largest available parcels in each province
        ```
        *Finds: Major land parcels across Netherlands*

        """
                
                response += """## 🎯 Ready-to-Test Parcel Examples

        **🚀 Quick Tests** (copy and paste):

        1. **"Show me large land parcels near Utrecht University"**
        2. **"Find parcels with area > 2000m² in Amsterdam"**
        3. **"Get property boundaries around Rotterdam Central Station"**
        4. **"Show me agricultural land near Groningen"**

        ## 🔧 Customization Tips

        **Change Location**:
        - University → City center, train station, specific address
        - Amsterdam → Any Dutch city or region

        **Adjust Size Filters**:
        - 1000m² → Any area (500m², 5000m², 10000m²)
        - Use > for minimum, < for maximum, or ranges

        **Land Use Types**:
        - Agricultural → Residential, commercial, industrial
        - Urban → Rural, suburban, development zones

        ---

        **Ready to explore land data?** Pick any example above or ask me to "run parcel example 1"!

        What type of land information interests you most?"""

        return response