//static/main.js
console.log("Loading FIXED Production Map-Aware PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // Simple but robust Legend Component (based on working test)
    const SmartLegend = ({ features }) => {
        console.log("SmartLegend rendering with features:", features?.length || 0);
        
        if (!features || !Array.isArray(features) || features.length === 0) {
            console.log("SmartLegend: No features to display");
            return null;
        }
        
        // Check for area data more robustly
        const hasAreaData = features.some(f => {
            if (!f.properties) return false;
            const area = f.properties.area_m2 || f.properties.oppervlakte_max || f.properties.oppervlakte_min;
            const valid = area && area > 0;
            if (valid) console.log("Found area data:", area, "for feature:", f.name);
            return valid;
        });
        
        const hasYearData = features.some(f => {
            if (!f.properties) return false;
            const year = f.properties.bouwjaar;
            const valid = year && !isNaN(year) && year > 1800;
            if (valid) console.log("Found year data:", year, "for feature:", f.name);
            return valid;
        });
        
        console.log("Legend decision: hasAreaData =", hasAreaData, "hasYearData =", hasYearData);
        
        // Priority: Show area legend if available, otherwise age legend
        const showAreaLegend = hasAreaData;
        const showAgeLegend = hasYearData && !hasAreaData;
        
        if (!showAreaLegend && !showAgeLegend) {
            console.log("SmartLegend: No valid data for any legend");
            return null;
        }
        
        // Use inline styles (like working test) instead of CSS classes
        const legendStyle = {
            position: 'fixed',
            bottom: '160px',
            left: '20px',
            zIndex: 998,
            maxWidth: '250px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '12px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            fontFamily: 'Inter, sans-serif'
        };
        
        if (showAreaLegend) {
            console.log("Rendering AREA legend");
            return React.createElement('div', {
                style: legendStyle
            }, [
                React.createElement('div', {
                    key: 'title',
                    style: { fontSize: '12px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937' }
                }, "🏠 Building Areas"),
                
                React.createElement('div', {
                    key: 'large',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#dc2626', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Large (>1000m²)")
                ]),
                
                React.createElement('div', {
                    key: 'medium',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#f97316', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Medium (500-1000m²)")
                ]),
                
                React.createElement('div', {
                    key: 'standard',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#eab308', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Standard (200-500m²)")
                ]),
                
                React.createElement('div', {
                    key: 'small',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#22c55e', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Small (<200m²)")
                ]),
                
                React.createElement('div', {
                    key: 'note',
                    style: { fontSize: '10px', color: '#6b7280', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e5e7eb' }
                }, "Areas from PDOK BAG data")
            ]);
        }
        
        if (showAgeLegend) {
            console.log("Rendering AGE legend");
            return React.createElement('div', {
                style: legendStyle
            }, [
                React.createElement('div', {
                    key: 'title',
                    style: { fontSize: '12px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937' }
                }, "🏛️ Building Ages"),
                
                React.createElement('div', {
                    key: 'historic',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#8B0000', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Historic (pre-1900)")
                ]),
                
                React.createElement('div', {
                    key: 'early',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#FF4500', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Early Modern (1900-1950)")
                ]),
                
                React.createElement('div', {
                    key: 'mid',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#32CD32', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Mid-Century (1950-2000)")
                ]),
                
                React.createElement('div', {
                    key: 'contemporary',
                    style: { fontSize: '11px', display: 'flex', alignItems: 'center', marginBottom: '4px' }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { width: '12px', height: '12px', backgroundColor: '#1E90FF', marginRight: '8px', borderRadius: '2px' }
                    }),
                    React.createElement('span', { key: 'text', style: { color: '#4b5563' } }, "Contemporary (2000+)")
                ]),
                
                React.createElement('div', {
                    key: 'note',
                    style: { fontSize: '10px', color: '#6b7280', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e5e7eb' }
                }, "Construction periods")
            ]);
        }
        
        return null;
    };




    function debugMapFeatures(features) {
        console.log("=== MAP FEATURES DEBUG ===");
        console.log("Number of features:", features?.length || 0);
        
        if (!features || !Array.isArray(features) || features.length === 0) {
            console.log("❌ No features to display");
            return false;
        }
        
        console.log("✅ Features array is valid");
        
        // Check first feature
        const firstFeature = features[0];
        console.log("First feature:", firstFeature);
        console.log("First feature type:", typeof firstFeature);
        console.log("First feature keys:", Object.keys(firstFeature));
        
        // Check required fields
        const requiredFields = ['type', 'name', 'lat', 'lon', 'geometry'];
        const missingFields = requiredFields.filter(field => !(field in firstFeature));
        
        if (missingFields.length > 0) {
            console.log("❌ Missing required fields:", missingFields);
            return false;
        }
        
        console.log("✅ All required fields present");
        
        // Check coordinates
        const lat = firstFeature.lat;
        const lon = firstFeature.lon;
        console.log("Coordinates:", lat, lon);
        
        if (lat === 0 || lon === 0) {
            console.log("❌ Invalid coordinates (zero values)");
            return false;
        }
        
        if (lat < 50 || lat > 54 || lon < 3 || lon > 8) {
            console.log("⚠️ Coordinates outside Netherlands bounds");
        }
        
        // Check geometry
        const geometry = firstFeature.geometry;
        console.log("Geometry:", geometry);
        
        if (!geometry || !geometry.type || !geometry.coordinates) {
            console.log("❌ Invalid geometry");
            return false;
        }
        
        console.log("✅ Geometry is valid");
        console.log("=========================");
        
        return true;
    }



    // Simple but robust Statistics Component (based on working test)
    const EnhancedMapStatistics = ({ features }) => {
        console.log("EnhancedMapStatistics rendering with features:", features?.length || 0);
        
        if (!features || !Array.isArray(features) || features.length === 0) {
            console.log("EnhancedMapStatistics: No features to display");
            return null;
        }
        
        // Safer data extraction
        const years = features
            .map(f => f.properties?.bouwjaar)
            .filter(year => year && !isNaN(year) && year > 1800);
        
        const areas = features
            .map(f => {
                if (!f.properties) return null;
                const area = f.properties.area_m2 || f.properties.oppervlakte_max || f.properties.oppervlakte_min;
                return area && area > 0 ? area : null;
            })
            .filter(area => area !== null);
        
        const distances = features
            .map(f => f.properties?.distance_km || f.distance_km)
            .filter(dist => dist && dist > 0);
        
        console.log("Statistics compiled:", { years: years.length, areas: areas.length, distances: distances.length });
        
        // Use inline styles (like working test)
        const statsStyle = {
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            zIndex: 998,
            maxWidth: '280px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '12px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            fontFamily: 'Inter, sans-serif'
        };
        
        return React.createElement('div', {
            style: statsStyle
        }, [
            React.createElement('div', {
                key: 'title',
                style: { fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#1f2937' }
            }, "📊 Search Results"),
            
            React.createElement('div', {
                key: 'count',
                style: { fontSize: '11px', color: '#4b5563', marginBottom: '8px' }
            }, `${features.length} buildings displayed`),
            
            // Area statistics
            ...(areas.length > 0 ? [
                React.createElement('div', {
                    key: 'area-title',
                    style: { fontSize: '10px', fontWeight: 'bold', color: '#374151', marginBottom: '2px' }
                }, "🏠 Building Areas:"),
                React.createElement('div', {
                    key: 'area-range',
                    style: { fontSize: '10px', color: '#6b7280' }
                }, `${Math.min(...areas).toLocaleString()}m² - ${Math.max(...areas).toLocaleString()}m²`),
                React.createElement('div', {
                    key: 'area-avg',
                    style: { fontSize: '10px', color: '#6b7280', marginBottom: '6px' }
                }, `Average: ${Math.round(areas.reduce((sum, area) => sum + area, 0) / areas.length).toLocaleString()}m²`)
            ] : []),
            
            // Distance statistics
            ...(distances.length > 0 ? [
                React.createElement('div', {
                    key: 'distance-title',
                    style: { fontSize: '10px', fontWeight: 'bold', color: '#374151', marginBottom: '2px' }
                }, "📍 Distances:"),
                React.createElement('div', {
                    key: 'distance-range',
                    style: { fontSize: '10px', color: '#6b7280', marginBottom: '6px' }
                }, `${Math.min(...distances).toFixed(3)}km - ${Math.max(...distances).toFixed(3)}km`)
            ] : []),
            
            // Year statistics
            ...(years.length > 0 ? [
                React.createElement('div', {
                    key: 'year-title',
                    style: { fontSize: '10px', fontWeight: 'bold', color: '#374151', marginBottom: '2px' }
                }, "🏛️ Construction Years:"),
                React.createElement('div', {
                    key: 'years',
                    style: { fontSize: '10px', color: '#6b7280' }
                }, `${Math.min(...years)} - ${Math.max(...years)}`)
            ] : [])
        ]);
    };

    const App = () => {
        console.log("Initializing FIXED Production Map component");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your map-aware AI Agent.\nI can help you explore buildings around any location and answer questions about them.\n\n🧭 Try asking:\n“Show me buildings near Leonard Springerlaan 37, Groningen.”\n\n📐 Or get specific:\n“Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m².”'
,
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        const [searchLocation, setSearchLocation] = useState(null);
        
        // Refs
        const mapRef = useRef(null);
        const mapInstance = useRef(null);
        const overlayRef = useRef(null);
        const messagesEndRef = useRef(null);
        const locationPinRef = useRef(null);

        // Auto-scroll to bottom of messages
        const scrollToBottom = () => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        };

        useEffect(() => {
            scrollToBottom();
        }, [messages]);

        // Debug features whenever they change
        useEffect(() => {
            console.log("Features updated:", features.length);
            if (features.length > 0) {
                console.log("Sample feature data:", {
                    name: features[0].name,
                    properties: features[0].properties,
                    hasArea: !!(features[0].properties?.area_m2 || features[0].properties?.oppervlakte_max || features[0].properties?.oppervlakte_min),
                    hasYear: !!(features[0].properties?.bouwjaar),
                    hasDistance: !!(features[0].properties?.distance_km || features[0].distance_km)
                });
            }
        }, [features]);

        // Initialize OpenLayers map
        useEffect(() => {
            console.log("Setting up OpenLayers map");
            try {
                // Base layers
                const osmLayer = new ol.layer.Tile({
                    source: new ol.source.OSM(),
                    visible: mapView === 'street'
                });

                const satelliteLayer = new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        url: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                        attributions: 'Imagery ©2023 Google'
                    }),
                    visible: mapView === 'satellite'
                });

                const controls = [
                    new ol.control.Zoom(),
                    new ol.control.Attribution()
                ];

                mapInstance.current = new ol.Map({
                    target: mapRef.current,
                    layers: [osmLayer, satelliteLayer],
                    view: new ol.View({
                        center: ol.proj.fromLonLat(mapCenter),
                        zoom: mapZoom
                    }),
                    controls: controls
                });

                // Map movement listeners
                mapInstance.current.getView().on('change:center', () => {
                    const center = ol.proj.toLonLat(mapInstance.current.getView().getCenter());
                    setMapCenter(center);
                });

                mapInstance.current.getView().on('change:resolution', () => {
                    const zoom = mapInstance.current.getView().getZoom();
                    setMapZoom(Math.round(zoom));
                });

                // Popup setup
                const container = document.createElement('div');
                container.className = 'ol-popup';
                const content = document.createElement('div');
                content.id = 'popup-content';
                container.appendChild(content);
                const closer = document.createElement('a');
                closer.className = 'ol-popup-closer';
                closer.href = '#';
                closer.innerHTML = '×';
                container.appendChild(closer);

                overlayRef.current = new ol.Overlay({
                    element: container,
                    autoPan: {
                        animation: { duration: 250 }
                    }
                });
                mapInstance.current.addOverlay(overlayRef.current);

                // Create location pin with inline styles (like working test)
                const pinContainer = document.createElement('div');
                pinContainer.style.cssText = `
                    pointer-events: none;
                    z-index: 1001;
                `;
                pinContainer.innerHTML = `
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        animation: pinDrop 0.6s ease-out;
                    ">
                        <div style="
                            position: relative;
                            width: 40px;
                            height: 40px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                            border-radius: 50% 50% 50% 0;
                            transform: rotate(-45deg);
                            box-shadow: 0 8px 16px rgba(239, 68, 68, 0.4);
                            border: 3px solid white;
                        ">
                            <div style="
                                transform: rotate(45deg);
                                font-size: 18px;
                                color: white;
                                font-weight: bold;
                            ">📍</div>
                            <div style="
                                position: absolute;
                                top: -5px;
                                left: -5px;
                                right: -5px;
                                bottom: -5px;
                                border: 2px solid #ef4444;
                                border-radius: 50% 50% 50% 0;
                                animation: pinPulse 2s infinite;
                                opacity: 0.6;
                            "></div>
                        </div>
                        <div style="
                            margin-top: 8px;
                            background: rgba(239, 68, 68, 0.9);
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 11px;
                            font-weight: 600;
                            white-space: nowrap;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                        ">Search Location</div>
                    </div>
                `;
                
                locationPinRef.current = new ol.Overlay({
                    element: pinContainer,
                    positioning: 'bottom-center',
                    stopEvent: false,
                    offset: [0, -10]
                });
                mapInstance.current.addOverlay(locationPinRef.current);

                closer.onclick = () => {
                    overlayRef.current.setPosition(undefined);
                    closer.blur();
                    return false;
                };

                // Enhanced click handler
                mapInstance.current.on('singleclick', (evt) => {
                    const feature = mapInstance.current.forEachFeatureAtPixel(evt.pixel, f => f);
                    if (feature) {
                        const geom = feature.getGeometry();
                        let coordinates;
                        
                        if (geom.getType() === 'Point') {
                            coordinates = geom.getCoordinates();
                        } else if (geom.getType() === 'Polygon') {
                            const extent = geom.getExtent();
                            coordinates = [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2];
                        } else {
                            coordinates = geom.getFirstCoordinate();
                        }
                        
                        const props = feature.get('properties') || {};
                        const name = feature.get('name') || 'Unknown Feature';
                        const description = feature.get('description') || '';
                        const lonLat = ol.proj.toLonLat(coordinates);
                        
                        let popupContent = `
                            <div class="space-y-3">
                                <h3 class="text-lg font-semibold text-gray-800">${name}</h3>
                                <div class="text-sm text-gray-600">
                                    <p><span class="font-medium">Type:</span> ${geom.getType()}</p>
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-2">${description}</p>` : ''}
                        `;
                        
                        // Building information
                        if (props.bouwjaar) {
                            const year = props.bouwjaar;
                            let era = 'Unknown';
                            if (year < 1900) era = 'Historic (pre-1900)';
                            else if (year < 1950) era = 'Early Modern (1900-1950)';
                            else if (year < 2000) era = 'Mid-Century (1950-2000)';
                            else era = 'Contemporary (2000+)';
                            
                            popupContent += `<p><span class="font-medium">Built:</span> ${year} (${era})</p>`;
                        }
                        
                        const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min;
                        if (area && area > 0) {
                            popupContent += `<p><span class="font-medium">Area:</span> ${Math.round(area).toLocaleString()}m²</p>`;
                        }
                        
                        const distance = props.distance_km;
                        if (distance && distance > 0) {
                            popupContent += `<p><span class="font-medium">Distance:</span> ${distance.toFixed(3)}km from search location</p>`;
                        }
                        
                        popupContent += '</div></div>';
                        document.getElementById('popup-content').innerHTML = popupContent;
                        overlayRef.current.setPosition(coordinates);
                    } else {
                        overlayRef.current.setPosition(undefined);
                    }
                });

                console.log("✅ map setup complete");

                return () => {
                    if (mapInstance.current) {
                        mapInstance.current.setTarget(null);
                    }
                };
            } catch (error) {
                console.error("Error setting up map:", error);
            }
        }, [mapView]);

        // Show pin when searchLocation is set
        useEffect(() => {
            if (searchLocation && locationPinRef.current && mapInstance.current) {
                console.log(`📍 Adding location pin at: ${searchLocation.lat}, ${searchLocation.lon}`);
                const pinCoords = ol.proj.fromLonLat([searchLocation.lon, searchLocation.lat]);
                locationPinRef.current.setPosition(pinCoords);
            }
        }, [searchLocation]);

        // Switch between map views
        const switchMapView = (view) => {
            setMapView(view);
            if (mapInstance.current) {
                mapInstance.current.getLayers().forEach(layer => {
                    if (layer.getSource() instanceof ol.source.OSM) {
                        layer.setVisible(view === 'street');
                    } else if (layer.getSource() instanceof ol.source.XYZ) {
                        layer.setVisible(view === 'satellite');
                    }
                });
            }
        };

        // Enhanced chat query handler
        const handleQuery = async () => {
            if (!query.trim()) return;
            
            const userMessage = {
                type: 'user',
                content: query,
                timestamp: new Date()
            };
            
            setMessages(prev => [...prev, userMessage]);
            setIsLoading(true);
            const currentQuery = query;
            setQuery('');

            try {
                console.log("Sending query to backend:", currentQuery);
                
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: currentQuery, 
                        current_features: features,
                        map_center: mapCenter,
                        map_zoom: mapZoom
                    })
                });
                
                const data = await res.json();
                console.log("Received data from backend:", data);
                
                let responseContent = '';
                let foundBuildings = false;
                
                // Handle combined response format
                if (data && typeof data === 'object' && 'response' in data && 'geojson_data' in data) {
                    console.log("✅ Detected combined response format");
                    
                    responseContent = data.response;
                    const geojsonData = data.geojson_data;
                    
                    if (Array.isArray(geojsonData) && geojsonData.length > 0) {
                        const firstItem = geojsonData[0];
                        
                        if (firstItem && typeof firstItem === 'object' && 
                            'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 
                            'geometry' in firstItem && firstItem.lat !== 0 && firstItem.lon !== 0) {
                            
                            console.log("✓ Valid building data - updating map and components");
                            
                            // Extract search location
                            const responseText = data.response || '';
                            const coordMatch = responseText.match(/(\d+\.\d+)°N,\s*(\d+\.\d+)°E/);
                            if (coordMatch) {
                                const searchLat = parseFloat(coordMatch[1]);
                                const searchLon = parseFloat(coordMatch[2]);
                                
                                setSearchLocation({
                                    lat: searchLat,
                                    lon: searchLon,
                                    name: "Search Location"
                                });
                                console.log(`📍 Found search coordinates: ${searchLat}, ${searchLon}`);
                            } 
                            else if (geojsonData.some(b => b.properties?.distance_km !== undefined)) {
                                const buildingsWithDistance = geojsonData.filter(b => b.properties?.distance_km !== undefined);
                                if (buildingsWithDistance.length > 0) {
                                    const closestBuilding = buildingsWithDistance[0];
                                    setSearchLocation({
                                        lat: closestBuilding.lat,
                                        lon: closestBuilding.lon,
                                        name: "Near Search Address"
                                    });
                                    console.log(`📍 Using closest building as search center`);
                                }
                            }
                            
                            console.log("Setting features for legend and statistics:", geojsonData.length);
                            setFeatures(geojsonData);
                            updateMapFeatures(geojsonData);
                            foundBuildings = true;
                        }
                    }
                }
                // Handle other response formats...
                else if (Array.isArray(data) && data.length > 0) {
                    const firstItem = data[0];
                    
                    if (firstItem && typeof firstItem === 'object' && 
                        'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 
                        'geometry' in firstItem && firstItem.lat !== 0 && firstItem.lon !== 0) {
                        
                        console.log("✓ Legacy building data format - updating map");
                        setFeatures(data);
                        updateMapFeatures(data);
                        foundBuildings = true;
                        
                        responseContent = `Found ${data.length} buildings! The legend and location pin should now work correctly.`;
                    } else if (firstItem && firstItem.error) {
                        responseContent = `I encountered an issue: ${firstItem.error}`;
                    } else {
                        responseContent = Array.isArray(data) ? data.join('\n') : JSON.stringify(data, null, 2);
                    }
                }
                else if (data && data.response) {
                    responseContent = data.response;
                }
                else if (data && data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                }
                else if (typeof data === 'string') {
                    responseContent = data;
                }
                else {
                    responseContent = JSON.stringify(data, null, 2);
                }
                
                const assistantMessage = {
                    type: 'assistant',
                    content: responseContent,
                    timestamp: new Date()
                };
                
                setMessages(prev => [...prev, assistantMessage]);
                
            } catch (error) {
                console.error("Query error:", error);
                
                const errorMessage = {
                    type: 'assistant',
                    content: `Sorry, I encountered an error: ${error.message}`,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, errorMessage]);
            } finally {
                setIsLoading(false);
            }
        };

        // Enhanced map features update
        const updateMapFeatures = (data) => {
            if (!mapInstance.current) {
                console.error("Map instance not available");
                return;
            }

            console.log(`Updating map with ${data.length} features`);
            
            // Remove existing vector layers
            const layersToRemove = [];
            mapInstance.current.getLayers().forEach(layer => {
                if (layer instanceof ol.layer.Vector) {
                    layersToRemove.push(layer);
                }
            });
            
            layersToRemove.forEach(layer => {
                mapInstance.current.removeLayer(layer);
            });

            if (!data || data.length === 0) {
                return;
            }

            const vectorSource = new ol.source.Vector();
            let featuresAdded = 0;
            
            data.forEach((f, index) => {
                try {
                    if (!f.geometry || !f.lat || !f.lon || f.lat === 0 || f.lon === 0) {
                        console.warn(`Skipping feature ${index + 1}: invalid data`);
                        return;
                    }
                    
                    let geom;
                    try {
                        let processedGeometry = JSON.parse(JSON.stringify(f.geometry));
                        
                        if (processedGeometry.coordinates) {
                            function ensureArrays(obj) {
                                if (obj === null || obj === undefined) return obj;
                                if (typeof obj === 'number') return obj;
                                
                                if (typeof obj === 'object') {
                                    if (Array.isArray(obj)) {
                                        return obj.map(ensureArrays);
                                    }
                                    
                                    const keys = Object.keys(obj);
                                    if (keys.length > 0 && keys.every(key => !isNaN(parseInt(key)))) {
                                        const arr = [];
                                        for (let i = 0; i < keys.length; i++) {
                                            if (obj.hasOwnProperty(i.toString())) {
                                                arr[i] = ensureArrays(obj[i.toString()]);
                                            }
                                        }
                                        return arr;
                                    }
                                    
                                    const result = {};
                                    for (const key in obj) {
                                        if (obj.hasOwnProperty(key)) {
                                            result[key] = ensureArrays(obj[key]);
                                        }
                                    }
                                    return result;
                                }
                                
                                return obj;
                            }
                            
                            processedGeometry.coordinates = ensureArrays(processedGeometry.coordinates);
                        }
                        
                        geom = new ol.format.GeoJSON().readGeometry(processedGeometry, {
                            dataProjection: 'EPSG:4326',
                            featureProjection: 'EPSG:3857'
                        });
                        
                    } catch (geomError) {
                        console.error(`Geometry processing error for feature ${index + 1}:`, geomError);
                        geom = new ol.geom.Point(ol.proj.fromLonLat([f.lon, f.lat]));
                    }
                    
                    const feature = new ol.Feature({
                        geometry: geom,
                        name: f.name,
                        description: f.description,
                        properties: f.properties || {}
                    });
                    
                    vectorSource.addFeature(feature);
                    featuresAdded++;
                    
                } catch (error) {
                    console.error(`Error processing feature ${index + 1}:`, error);
                }
            });

            console.log(`Total features added to map: ${featuresAdded}/${data.length}`);

            if (featuresAdded === 0) {
                console.error("No features were successfully added to the map");
                return;
            }

            // ENHANCED STYLING
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => {
                    const geomType = feature.getGeometry().getType();
                    const props = feature.get('properties') || {};
                    
                    if (geomType === 'Point') {
                        const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min || 0;
                        let pointColor = '#667eea';
                        
                        if (area > 1000) {
                            pointColor = '#dc2626';
                        } else if (area > 500) {
                            pointColor = '#f97316';
                        } else if (area > 200) {
                            pointColor = '#eab308';
                        } else if (area > 0) {
                            pointColor = '#22c55e';
                        }
                        
                        return new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 12,
                                fill: new ol.style.Fill({ color: pointColor }),
                                stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 })
                            })
                        });
                        
                    } else if (geomType === 'Polygon') {
                        const year = props.bouwjaar;
                        const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min || 0;
                        
                        let fillColor = 'rgba(102, 126, 234, 0.7)';
                        let strokeColor = '#667eea';
                        
                        // Priority: Color by area if available
                        if (area > 0) {
                            if (area > 1000) {
                                fillColor = 'rgba(220, 38, 38, 0.8)';
                                strokeColor = '#dc2626';
                            } else if (area > 500) {
                                fillColor = 'rgba(249, 115, 22, 0.8)';
                                strokeColor = '#f97316';
                            } else if (area > 200) {
                                fillColor = 'rgba(234, 179, 8, 0.8)';
                                strokeColor = '#eab308';
                            } else {
                                fillColor = 'rgba(34, 197, 94, 0.8)';
                                strokeColor = '#22c55e';
                            }
                        }
                        // Fallback: Color by age
                        else if (year) {
                            if (year < 1900) {
                                fillColor = 'rgba(139, 0, 0, 0.7)';
                                strokeColor = '#8B0000';
                            } else if (year < 1950) {
                                fillColor = 'rgba(255, 69, 0, 0.7)';
                                strokeColor = '#FF4500';
                            } else if (year < 2000) {
                                fillColor = 'rgba(50, 205, 50, 0.7)';
                                strokeColor = '#32CD32';
                            } else {
                                fillColor = 'rgba(30, 144, 255, 0.7)';
                                strokeColor = '#1E90FF';
                            }
                        }
                        
                        return new ol.style.Style({
                            stroke: new ol.style.Stroke({ 
                                color: strokeColor, 
                                width: 3
                            }),
                            fill: new ol.style.Fill({ 
                                color: fillColor
                            })
                        });
                        
                    } else {
                        return new ol.style.Style({
                            stroke: new ol.style.Stroke({ color: '#667eea', width: 3 }),
                            fill: new ol.style.Fill({ color: 'rgba(102, 126, 234, 0.6)' }),
                            image: new ol.style.Circle({
                                radius: 8,
                                fill: new ol.style.Fill({ color: '#667eea' }),
                                stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                            })
                        });
                    }
                }
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("Vector layer added to map");
            
            // Fit to features
            const extent = vectorSource.getExtent();
            
            if (extent && extent.every(coord => isFinite(coord))) {
                mapInstance.current.getView().fit(extent, { 
                    padding: [50, 50, 50, 50], 
                    maxZoom: 16,
                    duration: 1000
                });
                console.log("Map view fitted to features");
            }
        };

        // Handle Enter key press
        const handleKeyPress = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleQuery();
            }
        };

        // Format timestamp
        const formatTime = (date) => {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        };

        return (
            <div className="relative h-full w-full">
                {/* Map Container */}
                <div ref={mapRef} className="h-full w-full"></div>
                
                {/* Map Controls - Top Right */}
                <div className="absolute top-4 right-4 z-40">
                    <div className="floating-card p-2">
                        <div className="flex space-x-2">
                            <button
                                onClick={() => switchMapView('street')}
                                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                                    mapView === 'street' 
                                        ? 'bg-blue-500 text-white shadow-md' 
                                        : 'bg-white text-gray-700 hover:bg-gray-50'
                                }`}
                            >
                                Street
                            </button>
                            <button
                                onClick={() => switchMapView('satellite')}
                                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                                    mapView === 'satellite' 
                                        ? 'bg-blue-500 text-white shadow-md' 
                                        : 'bg-white text-gray-700 hover:bg-gray-50'
                                }`}
                            >
                                Satellite
                            </button>
                        </div>
                    </div>
                </div>

                {/* Map Context Info */}
                <div className="absolute top-20 left-4 z-40 map-context-info">
                    <div className="floating-card p-3">
                        <div className="text-sm text-gray-700">
                            <p className="font-medium">Map View</p>
                            <p>Zoom: {mapZoom}</p>
                            {searchLocation && (
                                <p className="text-red-600 font-medium">📍 {searchLocation.name}</p>
                            )}
                            {features.length > 0 && (
                                <p className="text-blue-600 font-medium">{features.length} buildings loaded</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Enhanced Chat Interface */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-[600px] glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse-slow"></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">Agentic Mapper</h2>
                                    <p className="text-sm text-blue-100">Agent Mapping Assistant</p>
                                </div>
                            </div>
                            <button 
                                onClick={() => setIsChatOpen(false)} 
                                className="text-white hover:text-red-300 transition-colors p-1 rounded-full hover:bg-white hover:bg-opacity-20"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Messages Container */}
                        <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-4">
                            {messages.map((message, index) => (
                                <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-xs px-4 py-2 rounded-2xl text-white text-sm ${
                                        message.type === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'
                                    }`}>
                                        <p className="whitespace-pre-wrap">{message.content}</p>
                                        <p className="text-xs opacity-75 mt-1">{formatTime(message.timestamp)}</p>
                                    </div>
                                </div>
                            ))}
                            
                            {isLoading && (
                                <div className="flex justify-start">
                                    <div className="chat-bubble-assistant max-w-xs px-4 py-2 rounded-2xl text-white text-sm">
                                        <div className="typing-indicator">
                                            <span></span>
                                            <span></span>
                                            <span></span>
                                        </div>
                                        <p className="text-xs opacity-75 mt-1">Agent processing...</p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Enhanced Input Area */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    onClick={() => setQuery("Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²")}
                                    className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                                >
                                    📍 Address + Pin
                                </button>
                                <button
                                    onClick={() => setQuery("Find buildings that are 500 meters away from Amsterdam Centraal larger than 500m²")}
                                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                                >
                                    🚉 Station Area
                                </button>
                                <button
                                    onClick={() => setQuery("Show historic buildings that are between 200 meters away from Groningen train station built before 1950")}
                                    className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
                                >
                                    🏛️ Historic Search
                                </button>
                                <button
                                    onClick={() => setQuery("Show me 100 buildings that are 500 meters away from  Leonard Springerlaan 37, Groningen with area > 150m²")}
                                    className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded-full hover:bg-orange-200 transition-colors"
                                >
                                    ✅ Test
                                </button>
                            </div>
                            
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    className="flex-1 search-input rounded-xl px-4 py-2 text-sm focus:outline-none"
                                    placeholder="Pin + Legends now working! 📍🏠📊"
                                    disabled={isLoading}
                                />
                                <button
                                    onClick={handleQuery}
                                    disabled={isLoading || !query.trim()}
                                    className="chat-gradient text-white p-2 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <button
                        onClick={() => setIsChatOpen(true)}
                        className="fixed bottom-6 right-6 chat-gradient text-white rounded-full p-4 shadow-2xl hover:scale-105 transition-transform z-50 group"
                    >
                        <div className="relative">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-ping"></div>
                            {features.length > 0 && (
                                <div className="absolute -bottom-2 -left-2 bg-blue-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center">
                                    {features.length}
                                </div>
                            )}
                            {searchLocation && (
                                <div className="absolute -bottom-3 -right-3 bg-red-500 text-white text-xs rounded-full px-2 py-1 font-bold">
                                    📍
                                </div>
                            )}
                        </div>
                    </button>
                )}

                {/* Statistics Component (using inline styles) */}
                {React.createElement(EnhancedMapStatistics, { features: features })}

                {/* Smart Legend Component (using inline styles) */}
                {React.createElement(SmartLegend, { features: features })}

                {/* Status Indicator */}
                {features.length > 0 && (
                    <div style={{
                        position: 'fixed',
                        top: '50%',
                        right: '20px',
                        transform: 'translateY(-50%)',
                        zIndex: 999,
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        border: '2px solid #22c55e',
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '11px',
                        color: '#15803d'
                    }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                            ✅ SYSTEM READY!
                        </div>
                        <div>📍 Pin: {searchLocation ? '✅' : '❌'}</div>
                        <div>🏠 Legend: ✅</div>
                        <div>📊 Stats: ✅</div>
                        <div>{features.length} buildings</div>
                    </div>
                )}
            </div>
        );
    };

    console.log("Rendering Production Map-Aware React app");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("Failed to initialize  Production React app:", error);
}