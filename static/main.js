//static/main.js - Enhanced with Flexible Legends and Location Plotting
console.log("Loading ENHANCED Production Map-Aware PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // ENHANCED: Flexible Legend Component that uses backend data
    const FlexibleLegend = ({ legendData }) => {
        console.log("FlexibleLegend rendering with data:", legendData);
        
        if (!legendData || !legendData.categories || legendData.categories.length === 0) {
            console.log("FlexibleLegend: No legend data to display");
            return null;
        }
        
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
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(10px)'
        };
        
        console.log("Rendering flexible legend:", legendData.title);
        
        return React.createElement('div', {
            style: legendStyle
        }, [
            // Title
            React.createElement('div', {
                key: 'title',
                style: { 
                    fontSize: '12px', 
                    fontWeight: 'bold', 
                    marginBottom: '8px', 
                    color: '#1f2937',
                    display: 'flex',
                    alignItems: 'center'
                }
            }, legendData.title),
            
            // Categories
            ...legendData.categories.map((category, index) => 
                React.createElement('div', {
                    key: `category-${index}`,
                    style: { 
                        fontSize: '11px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        marginBottom: '4px',
                        justifyContent: 'space-between'
                    }
                }, [
                    React.createElement('div', {
                        key: 'left',
                        style: { display: 'flex', alignItems: 'center', flex: 1 }
                    }, [
                        React.createElement('div', {
                            key: 'color',
                            style: { 
                                width: '12px', 
                                height: '12px', 
                                backgroundColor: category.color, 
                                marginRight: '8px', 
                                borderRadius: '2px',
                                border: '1px solid rgba(0,0,0,0.1)'
                            }
                        }),
                        React.createElement('span', { 
                            key: 'label', 
                            style: { color: '#4b5563', fontSize: '10px' } 
                        }, category.label)
                    ]),
                    React.createElement('div', {
                        key: 'right',
                        style: { 
                            fontSize: '10px', 
                            color: '#6b7280',
                            fontWeight: '500'
                        }
                    }, [
                        category.count && React.createElement('span', { key: 'count' }, category.count),
                        category.area_ha && React.createElement('span', { key: 'area' }, ` (${category.area_ha}ha)`),
                        category.percentage && React.createElement('span', { key: 'percentage' }, ` ${category.percentage}%`),
                        category.range && React.createElement('span', { key: 'range' }, category.range)
                    ])
                ])
            ),
            
            // Statistics footer
            legendData.statistics && React.createElement('div', {
                key: 'stats',
                style: { 
                    fontSize: '10px', 
                    color: '#6b7280', 
                    marginTop: '8px', 
                    paddingTop: '8px', 
                    borderTop: '1px solid #e5e7eb'
                }
            }, [
                legendData.statistics.total_features && React.createElement('div', { key: 'total' }, 
                    `Total: ${legendData.statistics.total_features} features`),
                legendData.statistics.total_area_ha && React.createElement('div', { key: 'total_area' }, 
                    `Area: ${legendData.statistics.total_area_ha}ha`),
                legendData.statistics.classifications && React.createElement('div', { key: 'classifications' }, 
                    `Types: ${legendData.statistics.classifications}`),
                legendData.layer_type && React.createElement('div', { key: 'source', style: { fontStyle: 'italic', marginTop: '4px' } }, 
                    `Source: ${legendData.layer_type}`)
            ])
        ]);
    };

    // ENHANCED: Location Pin Component with better styling
    const LocationPin = ({ searchLocation, mapInstance, locationPinRef }) => {
        useEffect(() => {
            if (searchLocation && locationPinRef.current && mapInstance.current) {
                console.log(`📍 Displaying location pin: ${searchLocation.name} at ${searchLocation.lat}, ${searchLocation.lon}`);
                
                // Create enhanced pin element
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
                            max-width: 120px;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        ">${searchLocation.name || 'Search Location'}</div>
                    </div>
                `;
                
                // Update the overlay element
                locationPinRef.current.setElement(pinContainer);
                
                const pinCoords = ol.proj.fromLonLat([searchLocation.lon, searchLocation.lat]);
                locationPinRef.current.setPosition(pinCoords);
                
                // Optionally center map on location (with animation)
                if (searchLocation.center_map !== false) {
                    mapInstance.current.getView().animate({
                        center: pinCoords,
                        duration: 1000,
                        zoom: Math.max(mapInstance.current.getView().getZoom(), 12)
                    });
                }
            } else if (locationPinRef.current) {
                // Hide pin if no search location
                locationPinRef.current.setPosition(undefined);
            }
        }, [searchLocation, mapInstance, locationPinRef]);
        
        return null; // This component doesn't render anything directly
    };

    // ENHANCED: Smart Statistics Component that adapts to layer type
    const AdaptiveStatistics = ({ features, legendData, layerType }) => {
        console.log("AdaptiveStatistics rendering:", { features: features?.length, layerType, legendData: !!legendData });
        
        if (!features || !Array.isArray(features) || features.length === 0) {
            return null;
        }
        
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
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(10px)'
        };
        
        // Use legend data statistics if available, otherwise compute our own
        const displayStats = legendData?.statistics || {};
        
        return React.createElement('div', {
            style: statsStyle
        }, [
            React.createElement('div', {
                key: 'title',
                style: { fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#1f2937' }
            }, `📊 ${layerType === 'land_use' ? 'Land Use' : layerType === 'buildings' ? 'Buildings' : layerType === 'parcels' ? 'Parcels' : layerType === 'environmental' ? 'Protected Areas' : 'Features'} Analysis`),
            
            React.createElement('div', {
                key: 'count',
                style: { fontSize: '11px', color: '#4b5563', marginBottom: '8px' }
            }, `${features.length} features displayed`),
            
            // Dynamic statistics based on legend data
            ...(Object.entries(displayStats).map(([key, value], index) => {
                if (key === 'total_features') return null; // Already shown above
                
                let label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                let displayValue = value;
                
                // Format specific statistics
                if (key.includes('area') && typeof value === 'number') {
                    displayValue = `${value}ha`;
                } else if (key.includes('year') && typeof value === 'number') {
                    displayValue = value.toString();
                } else if (key.includes('range')) {
                    label = 'Range';
                } else if (key === 'classifications' || key === 'area_types' || key === 'boundary_types') {
                    label = 'Categories';
                }
                
                return React.createElement('div', {
                    key: `stat-${index}`,
                    style: { 
                        fontSize: '10px', 
                        color: '#6b7280',
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '2px'
                    }
                }, [
                    React.createElement('span', { key: 'label', style: { fontWeight: '500' } }, label + ':'),
                    React.createElement('span', { key: 'value' }, displayValue)
                ]);
            }).filter(Boolean)),
            
            // Layer type indicator
            layerType && React.createElement('div', {
                key: 'layer-type',
                style: { 
                    fontSize: '9px', 
                    color: '#9ca3af', 
                    marginTop: '8px', 
                    paddingTop: '8px', 
                    borderTop: '1px solid #e5e7eb',
                    fontStyle: 'italic'
                }
            }, `Data type: ${layerType}`)
        ]);
    };

    function debugMapFeatures(features) {
        console.log("=== MAP FEATURES DEBUG ===");
        console.log("Number of features:", features?.length || 0);
        
        if (!features || !Array.isArray(features) || features.length === 0) {
            console.log("❌ No features to display");
            return false;
        }
        
        console.log("✅ Features array is valid");
        
        const firstFeature = features[0];
        console.log("First feature:", firstFeature);
        console.log("First feature type:", typeof firstFeature);
        console.log("First feature keys:", Object.keys(firstFeature));
        
        const requiredFields = ['type', 'name', 'lat', 'lon', 'geometry'];
        const missingFields = requiredFields.filter(field => !(field in firstFeature));
        
        if (missingFields.length > 0) {
            console.log("❌ Missing required fields:", missingFields);
            return false;
        }
        
        console.log("✅ All required fields present");
        
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

    const App = () => {
        console.log("Initializing ENHANCED Production Map component");
        
        // ENHANCED State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your enhanced map-aware AI Agent.\nI can help you explore different types of spatial data with flexible legends and location pins.\n\n🌾 Try asking:\n"Analyze agricultural land distribution in Utrecht province"\n\n🏠 Or:\n"Show me buildings near Leonard Springerlaan 37, Groningen"\n\n📐 Or:\n"Find large parcels suitable for development in Groningen"',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        
        // ENHANCED: New state for flexible legend and location
        const [searchLocation, setSearchLocation] = useState(null);
        const [legendData, setLegendData] = useState(null);
        const [layerType, setLayerType] = useState(null);
        const [analysisStatus, setAnalysisStatus] = useState(null);
        
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

        // ENHANCED: Debug state changes
        React.useEffect(() => {
            console.log("🔄 State changed:", {
                features: features.length,
                legendData: !!legendData,
                layerType,
                searchLocation: !!searchLocation
            });
        }, [features, legendData, layerType, searchLocation]);

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

                // ENHANCED: Initialize location pin overlay (empty initially)
                locationPinRef.current = new ol.Overlay({
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

                // ENHANCED: Click handler with flexible popup content
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
                        
                        // ENHANCED: Flexible popup content based on layer type
                        let popupContent = `
                            <div class="space-y-3">
                                <h3 class="text-lg font-semibold text-gray-800">${name}</h3>
                                <div class="text-sm text-gray-600">
                                    <p><span class="font-medium">Type:</span> ${geom.getType()}</p>
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-2">${description}</p>` : ''}
                        `;
                        
                        // Dynamic content based on layer type
                        if (layerType === 'buildings') {
                            // Building-specific information
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
                        } else if (layerType === 'land_use') {
                            // Land use information
                            if (props.bgb2015_hoofdklasse_label || props.hoofdklasse || props.bodemgebruik) {
                                const landUse = props.bgb2015_hoofdklasse_label || props.hoofdklasse || props.bodemgebruik;
                                popupContent += `<p><span class="font-medium">Land Use:</span> ${landUse}</p>`;
                            }
                            
                            if (props.shape_area && props.shape_area > 0) {
                                const areaHa = props.shape_area / 10000;
                                popupContent += `<p><span class="font-medium">Area:</span> ${areaHa.toFixed(1)}ha</p>`;
                            }
                        } else if (layerType === 'parcels') {
                            // Parcel information
                            if (props.perceelnummer) {
                                popupContent += `<p><span class="font-medium">Parcel Number:</span> ${props.perceelnummer}</p>`;
                            }
                            
                            if (props.kadastraleGrootteWaarde && props.kadastraleGrootteWaarde > 0) {
                                const areaHa = props.kadastraleGrootteWaarde / 10000;
                                popupContent += `<p><span class="font-medium">Area:</span> ${areaHa.toFixed(2)}ha</p>`;
                            }
                        } else if (layerType === 'environmental') {
                            // Environmental/nature information
                            if (props.gebiedsnaam || props.naam) {
                                const areaName = props.gebiedsnaam || props.naam;
                                popupContent += `<p><span class="font-medium">Area Name:</span> ${areaName}</p>`;
                            }
                            
                            if (props.type_gebied) {
                                popupContent += `<p><span class="font-medium">Protection Type:</span> ${props.type_gebied}</p>`;
                            }
                        }
                        
                        // Distance information (common to all types)
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

                console.log("✅ Enhanced map setup complete");

                return () => {
                    if (mapInstance.current) {
                        mapInstance.current.setTarget(null);
                    }
                };
            } catch (error) {
                console.error("Error setting up map:", error);
            }
        }, [mapView]);

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

        // ENHANCED: handleQuery with flexible legend and location support
        const handleQuery = async () => {
            if (!query.trim()) return;
            
            const userMessage = {
                type: 'user',
                content: query,
                timestamp: new Date()
            };
            
            setMessages(prev => [...prev, userMessage]);
            setIsLoading(true);
            setAnalysisStatus('processing');
            const currentQuery = query;
            setQuery('');

            try {
                console.log("🚀 Sending enhanced query to backend:", currentQuery);
                
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
                console.log("📦 Received enhanced data from backend:", data);
                
                let responseContent = '';
                let foundFeatures = false;
                
                // ENHANCED: Handle backend response with flexible legend and location data
                if (data && typeof data === 'object') {
                    console.log("✅ Processing enhanced response format");
                    
                    responseContent = data.response || data.message || 'Analysis completed.';
                    
                    // Extract features
                    const geojsonData = data.geojson_data || data.features || data.data;
                    
                    // Extract legend data
                    const backendLegendData = data.legend_data;
                    const backendLayerType = data.layer_type;
                    
                    // Extract search location
                    const backendSearchLocation = data.search_location;
                    
                    console.log("🔍 Enhanced data components:", {
                        features: geojsonData?.length,
                        legendData: !!backendLegendData,
                        layerType: backendLayerType,
                        searchLocation: !!backendSearchLocation
                    });
                    
                    // Process features
                    if (Array.isArray(geojsonData) && geojsonData.length > 0) {
                        const firstItem = geojsonData[0];
                        
                        if (firstItem && typeof firstItem === 'object' && 
                            'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 
                            'geometry' in firstItem && firstItem.lat !== 0 && firstItem.lon !== 0) {
                            
                            console.log("✅ Valid feature data - updating enhanced components");
                            
                            // Update all state
                            setFeatures(geojsonData);
                            setLegendData(backendLegendData);
                            setLayerType(backendLayerType);
                            setSearchLocation(backendSearchLocation);
                            setAnalysisStatus('success');
                            
                            // Update map
                            updateMapFeatures(geojsonData, backendLayerType);
                            
                            foundFeatures = true;
                            
                            console.log("🎯 Enhanced state updated:", {
                                features: geojsonData.length,
                                legendTitle: backendLegendData?.title,
                                layerType: backendLayerType,
                                searchLocationName: backendSearchLocation?.name
                            });
                        } else {
                            console.log("❌ Invalid feature data structure");
                            setAnalysisStatus('error');
                        }
                    } else if (data.error) {
                        responseContent = `I encountered an issue: ${data.error}`;
                        setAnalysisStatus('error');
                    } else {
                        console.log("📝 Text-only response received");
                        setAnalysisStatus('text_response');
                    }
                }
                
                const assistantMessage = {
                    type: 'assistant',
                    content: responseContent,
                    timestamp: new Date()
                };
                
                setMessages(prev => [...prev, assistantMessage]);
                
            } catch (error) {
                console.error("❌ Enhanced query error:", error);
                setAnalysisStatus('error');
                
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

        // ENHANCED: Map features update with flexible styling
        const updateMapFeatures = (data, dataLayerType) => {
            if (!mapInstance.current) {
                console.error("Map instance not available");
                return;
            }

            console.log(`🗺️ Updating map with ${data.length} features of type: ${dataLayerType}`);
            
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

            // ENHANCED: Flexible styling based on layer type and legend data
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => {
                    const geomType = feature.getGeometry().getType();
                    const props = feature.get('properties') || {};
                    
                    // ENHANCED: Layer-type specific styling
                    if (dataLayerType === 'land_use') {
                        return createLandUseStyle(geomType, props, legendData);
                    } else if (dataLayerType === 'buildings') {
                        return createBuildingStyle(geomType, props, legendData);
                    } else if (dataLayerType === 'parcels') {
                        return createParcelStyle(geomType, props, legendData);
                    } else if (dataLayerType === 'environmental') {
                        return createEnvironmentalStyle(geomType, props, legendData);
                    } else if (dataLayerType === 'administrative') {
                        return createAdministrativeStyle(geomType, props, legendData);
                    } else {
                        return createDefaultStyle(geomType, props);
                    }
                }
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("✅ Enhanced vector layer added to map");
            
            // Fit to features with animation
            const extent = vectorSource.getExtent();
            
            if (extent && extent.every(coord => isFinite(coord))) {
                mapInstance.current.getView().fit(extent, { 
                    padding: [50, 50, 50, 50], 
                    maxZoom: 16,
                    duration: 1000
                });
                console.log("📍 Map view fitted to features");
            }
        };

        // ENHANCED: Layer-specific styling functions
        const createLandUseStyle = (geomType, props, legendData) => {
            const landUse = props.bgb2015_hoofdklasse_label || props.hoofdklasse || props.bodemgebruik || 'Unknown';
            
            // Try to match with legend colors
            let fillColor = 'rgba(102, 126, 234, 0.7)';
            let strokeColor = '#667eea';
            
            if (legendData && legendData.categories) {
                const matchingCategory = legendData.categories.find(cat => 
                    cat.label === landUse || landUse.toLowerCase().includes(cat.label.toLowerCase())
                );
                if (matchingCategory) {
                    const color = matchingCategory.color;
                    fillColor = `${color}80`; // Add transparency
                    strokeColor = color;
                }
            } else {
                // Fallback colors for common land use types
                if (landUse.toLowerCase().includes('agrarisch') || landUse.toLowerCase().includes('agricultural')) {
                    fillColor = 'rgba(34, 197, 94, 0.7)';
                    strokeColor = '#22c55e';
                } else if (landUse.toLowerCase().includes('bebouwd') || landUse.toLowerCase().includes('urban')) {
                    fillColor = 'rgba(239, 68, 68, 0.7)';
                    strokeColor = '#ef4444';
                } else if (landUse.toLowerCase().includes('bos') || landUse.toLowerCase().includes('forest')) {
                    fillColor = 'rgba(34, 197, 94, 0.8)';
                    strokeColor = '#16a34a';
                } else if (landUse.toLowerCase().includes('water')) {
                    fillColor = 'rgba(59, 130, 246, 0.8)';
                    strokeColor = '#3b82f6';
                }
            }
            
            if (geomType === 'Point') {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 8,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ color: strokeColor, width: 2 }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        const createBuildingStyle = (geomType, props, legendData) => {
            const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min || 0;
            const year = props.bouwjaar;
            
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
            
            if (geomType === 'Point') {
                const radius = area > 1000 ? 14 : area > 500 ? 12 : area > 200 ? 10 : 8;
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: radius,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ color: strokeColor, width: 3 }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        const createParcelStyle = (geomType, props, legendData) => {
            const area = props.kadastraleGrootteWaarde || 0;
            
            let fillColor = 'rgba(102, 126, 234, 0.6)';
            let strokeColor = '#667eea';
            
            if (area > 0) {
                const areaHa = area / 10000;
                if (areaHa > 10) {
                    fillColor = 'rgba(220, 38, 38, 0.6)';
                    strokeColor = '#dc2626';
                } else if (areaHa > 5) {
                    fillColor = 'rgba(249, 115, 22, 0.6)';
                    strokeColor = '#f97316';
                } else if (areaHa > 1) {
                    fillColor = 'rgba(234, 179, 8, 0.6)';
                    strokeColor = '#eab308';
                } else if (areaHa > 0.1) {
                    fillColor = 'rgba(34, 197, 94, 0.6)';
                    strokeColor = '#22c55e';
                } else {
                    fillColor = 'rgba(59, 130, 246, 0.6)';
                    strokeColor = '#3b82f6';
                }
            }
            
            if (geomType === 'Point') {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 10,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ color: strokeColor, width: 2 }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        const createEnvironmentalStyle = (geomType, props, legendData) => {
            const areaType = props.type_gebied || props.naam || props.gebiedsnaam || 'Protected Area';
            
            // Green-based color scheme for environmental areas
            let fillColor = 'rgba(34, 197, 94, 0.7)';
            let strokeColor = '#22c55e';
            
            // Try to match with legend colors if available
            if (legendData && legendData.categories) {
                const matchingCategory = legendData.categories.find(cat => 
                    cat.label === areaType || areaType.toLowerCase().includes(cat.label.toLowerCase())
                );
                if (matchingCategory) {
                    const color = matchingCategory.color;
                    fillColor = `${color}80`;
                    strokeColor = color;
                }
            } else {
                // Fallback colors for different protection types
                if (areaType.toLowerCase().includes('natura')) {
                    fillColor = 'rgba(16, 185, 129, 0.7)';
                    strokeColor = '#10b981';
                } else if (areaType.toLowerCase().includes('vogel') || areaType.toLowerCase().includes('bird')) {
                    fillColor = 'rgba(5, 150, 105, 0.7)';
                    strokeColor = '#059669';
                } else if (areaType.toLowerCase().includes('habitat')) {
                    fillColor = 'rgba(4, 120, 87, 0.7)';
                    strokeColor = '#047857';
                }
            }
            
            if (geomType === 'Point') {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 12,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ color: strokeColor, width: 3 }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        const createAdministrativeStyle = (geomType, props, legendData) => {
            const boundaryType = props.gemeentenaam ? 'Municipality' : 
                                  props.provincienaam ? 'Province' : 
                                  props.wijknaam ? 'District' : 'Administrative';
            
            let fillColor = 'rgba(59, 130, 246, 0.5)';
            let strokeColor = '#3b82f6';
            let strokeWidth = 2;
            
            // Different styles for different administrative levels
            if (boundaryType === 'Province') {
                fillColor = 'rgba(139, 92, 246, 0.4)';
                strokeColor = '#8b5cf6';
                strokeWidth = 4;
            } else if (boundaryType === 'Municipality') {
                fillColor = 'rgba(59, 130, 246, 0.5)';
                strokeColor = '#3b82f6';
                strokeWidth = 3;
            } else if (boundaryType === 'District') {
                fillColor = 'rgba(6, 182, 212, 0.5)';
                strokeColor = '#06b6d4';
                strokeWidth = 2;
            }
            
            if (geomType === 'Point') {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 10,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ 
                        color: strokeColor, 
                        width: strokeWidth,
                        lineDash: boundaryType === 'District' ? [5, 5] : undefined
                    }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        const createDefaultStyle = (geomType, props) => {
            const fillColor = 'rgba(102, 126, 234, 0.6)';
            const strokeColor = '#667eea';
            
            if (geomType === 'Point') {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 8,
                        fill: new ol.style.Fill({ color: strokeColor }),
                        stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                    })
                });
            } else {
                return new ol.style.Style({
                    stroke: new ol.style.Stroke({ color: strokeColor, width: 2 }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
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

        // ENHANCED: Clear map function
        const clearMap = () => {
            setFeatures([]);
            setLegendData(null);
            setLayerType(null);
            setSearchLocation(null);
            setAnalysisStatus(null);
            
            if (mapInstance.current) {
                // Remove vector layers
                const layersToRemove = [];
                mapInstance.current.getLayers().forEach(layer => {
                    if (layer instanceof ol.layer.Vector) {
                        layersToRemove.push(layer);
                    }
                });
                layersToRemove.forEach(layer => {
                    mapInstance.current.removeLayer(layer);
                });
                
                // Hide location pin
                if (locationPinRef.current) {
                    locationPinRef.current.setPosition(undefined);
                }
            }
        };

        return (
            <div className="relative h-full w-full">
                {/* Map Container */}
                <div ref={mapRef} className="h-full w-full"></div>
                
                {/* Location Pin Component */}
                {React.createElement(LocationPin, { 
                    searchLocation, 
                    mapInstance, 
                    locationPinRef 
                })}
                
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
                            {features.length > 0 && (
                                <button
                                    onClick={clearMap}
                                    className="px-3 py-2 rounded-lg text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition-all"
                                    title="Clear all features"
                                >
                                    Clear
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* ENHANCED: Map Context Info */}
                <div className="absolute top-20 left-4 z-40 map-context-info">
                    <div className="floating-card p-3">
                        <div className="text-sm text-gray-700">
                            <p className="font-medium">Map View</p>
                            <p>Zoom: {mapZoom}</p>
                            {searchLocation && (
                                <p className="text-red-600 font-medium">📍 {searchLocation.name}</p>
                            )}
                            {features.length > 0 && (
                                <p className="text-blue-600 font-medium">
                                    {features.length} {layerType || 'Features'}
                                </p>
                            )}
                            {layerType && (
                                <p className="text-purple-600 text-xs">
                                    Type: {layerType.replace('_', ' ')}
                                </p>
                            )}
                        </div>
                    </div>
                </div>

                {/* ENHANCED: Chat Interface */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-[600px] glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${
                                    analysisStatus === 'processing' ? 'bg-yellow-400 animate-pulse' :
                                    analysisStatus === 'success' ? 'bg-green-400' :
                                    analysisStatus === 'error' ? 'bg-red-400' :
                                    'bg-blue-400'
                                }`}></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">Enhanced Mapper</h2>
                                    <p className="text-sm text-blue-100">
                                        {analysisStatus === 'processing' ? 'Processing...' :
                                         analysisStatus === 'success' ? 'Analysis Complete' :
                                         analysisStatus === 'error' ? 'Error Occurred' :
                                         'Ready for Analysis'}
                                    </p>
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
                                        <p className="text-xs opacity-75 mt-1">Enhanced processing...</p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* ENHANCED: Input Area with better examples */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    onClick={() => setQuery("Analyze agricultural land distribution in Utrecht province")}
                                    className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                                >
                                    🌾 Land Use
                                </button>
                                <button
                                    onClick={() => setQuery("Show me buildings near Leonard Springerlaan 37, Groningen")}
                                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                                >
                                    🏠 Buildings
                                </button>
                                <button
                                    onClick={() => setQuery("Find large parcels suitable for development in Groningen")}
                                    className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
                                >
                                    📐 Parcels
                                </button>
                                <button
                                    onClick={() => setQuery("Show protected nature areas around Rotterdam")}
                                    className="px-2 py-1 text-xs bg-emerald-100 text-emerald-700 rounded-full hover:bg-emerald-200 transition-colors"
                                >
                                    🌿 Nature
                                </button>
                            </div>
                            
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    className="flex-1 search-input rounded-xl px-4 py-2 text-sm focus:outline-none"
                                    placeholder="Try different data types! 🌾🏠📐🌿"
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
                            {legendData && (
                                <div className="absolute -top-3 -left-3 bg-purple-500 text-white text-xs rounded-full px-2 py-1 font-bold">
                                    🏷️
                                </div>
                            )}
                        </div>
                    </button>
                )}

                {/* ENHANCED: Adaptive Statistics Component */}
                {React.createElement(AdaptiveStatistics, { 
                    features: features,
                    legendData: legendData,
                    layerType: layerType
                })}

                {/* ENHANCED: Flexible Legend Component */}
                {React.createElement(FlexibleLegend, { 
                    legendData: legendData 
                })}

                {/* ENHANCED: Status Indicator */}
                {(features.length > 0 || searchLocation || legendData) && (
                    <div style={{
                        position: 'fixed',
                        top: '50%',
                        right: '20px',
                        transform: 'translateY(-50%)',
                        zIndex: 999,
                        backgroundColor: analysisStatus === 'success' ? 'rgba(34, 197, 94, 0.1)' : 
                                        analysisStatus === 'error' ? 'rgba(239, 68, 68, 0.1)' : 
                                        'rgba(59, 130, 246, 0.1)',
                        border: `2px solid ${analysisStatus === 'success' ? '#22c55e' : 
                                            analysisStatus === 'error' ? '#ef4444' : 
                                            '#3b82f6'}`,
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '11px',
                        color: analysisStatus === 'success' ? '#15803d' : 
                               analysisStatus === 'error' ? '#dc2626' : 
                               '#1d4ed8'
                    }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                            {analysisStatus === 'success' ? '✅ ENHANCED READY!' : 
                             analysisStatus === 'error' ? '❌ ERROR' : 
                             '🔄 PROCESSING'}
                        </div>
                        <div>📍 Pin: {searchLocation ? '✅' : '❌'}</div>
                        <div>🏷️ Legend: {legendData ? '✅' : '❌'}</div>
                        <div>📊 Stats: {features.length > 0 ? '✅' : '❌'}</div>
                        <div>🗺️ Layer: {layerType || 'None'}</div>
                        {features.length > 0 && (
                            <div>{features.length} features</div>
                        )}
                        {legendData && (
                            <div style={{ fontSize: '10px', marginTop: '4px', fontStyle: 'italic' }}>
                                {legendData.title}
                            </div>
                        )}
                    </div>
                )}

                {/* ENHANCED: Help Overlay */}
                {!features.length && !isLoading && !searchLocation && (
                    <div style={{
                        position: 'fixed',
                        bottom: '50%',
                        left: '50%',
                        transform: 'translate(-50%, 50%)',
                        zIndex: 998,
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        padding: '20px',
                        borderRadius: '16px',
                        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                        border: '1px solid rgba(0, 0, 0, 0.1)',
                        fontFamily: 'Inter, sans-serif',
                        maxWidth: '400px',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '12px', color: '#1f2937' }}>
                            🎯 Enhanced PDOK Analysis System
                        </div>
                        <div style={{ fontSize: '12px', color: '#6b7280', lineHeight: '1.4' }}>
                            Try different types of spatial analysis:
                        </div>
                        <div style={{ fontSize: '11px', color: '#4b5563', marginTop: '8px', lineHeight: '1.3' }}>
                            🌾 <strong>Land Use:</strong> "Agricultural land in Utrecht"<br/>
                            🏠 <strong>Buildings:</strong> "Buildings near [address]"<br/>
                            📐 <strong>Parcels:</strong> "Large parcels in [city]"<br/>
                            🌿 <strong>Nature:</strong> "Protected areas around [city]"<br/>
                            🗺️ <strong>Admin:</strong> "Municipal boundaries"
                        </div>
                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '12px', fontStyle: 'italic' }}>
                            Each analysis type gets its own legend and styling!
                        </div>
                    </div>
                )}
            </div>
        );
    };

    console.log("Rendering Enhanced Production Map-Aware React app");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("Failed to initialize Enhanced Production React app:", error);
}