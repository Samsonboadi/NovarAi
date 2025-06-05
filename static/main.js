//static/main.js - Improved with Better Location Pin Handling
console.log("Loading INTELLIGENT Production Map-Aware PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // IMPROVED: Better Location Pin Component
    const IntelligentLocationPin = ({ searchLocation, mapInstance, locationPinRef }) => {
        useEffect(() => {
            console.log("🔍 IntelligentLocationPin effect:", searchLocation);
            
            if (searchLocation && locationPinRef.current && mapInstance.current) {
                console.log(`📍 Creating location pin: ${searchLocation.name} at ${searchLocation.lat}, ${searchLocation.lon}`);
                
                // Validate coordinates
                const lat = parseFloat(searchLocation.lat);
                const lon = parseFloat(searchLocation.lon);
                
                if (isNaN(lat) || isNaN(lon)) {
                    console.error("❌ Invalid coordinates for location pin:", searchLocation);
                    return;
                }
                
                // Check Netherlands bounds
                if (lat < 50 || lat > 54 || lon < 3 || lon > 8) {
                    console.warn("⚠️ Coordinates outside Netherlands bounds:", lat, lon);
                }
                
                // Create enhanced pin element
                const pinContainer = document.createElement('div');
                pinContainer.style.cssText = `
                    pointer-events: none;
                    z-index: 1001;
                    position: relative;
                `;
                
                // Determine pin color based on source
                const pinColor = searchLocation.source === 'response_coordinates' ? '#ef4444' : 
                               searchLocation.source === 'feature_centroid' ? '#f59e0b' : '#ef4444';
                
                pinContainer.innerHTML = `
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        animation: pinDrop 0.8s ease-out;
                    ">
                        <div style="
                            position: relative;
                            width: 40px;
                            height: 40px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            background: linear-gradient(135deg, ${pinColor} 0%, ${pinColor}dd 100%);
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
                                border: 2px solid ${pinColor};
                                border-radius: 50% 50% 50% 0;
                                animation: pinPulse 2s infinite;
                                opacity: 0.6;
                            "></div>
                        </div>
                        <div style="
                            margin-top: 8px;
                            background: rgba(239, 68, 68, 0.95);
                            color: white;
                            padding: 6px 10px;
                            border-radius: 14px;
                            font-size: 11px;
                            font-weight: 600;
                            white-space: nowrap;
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
                            max-width: 150px;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            text-align: center;
                        ">${searchLocation.name || 'Search Location'}</div>
                    </div>
                `;
                
                // Update the overlay element
                locationPinRef.current.setElement(pinContainer);
                
                // Set position
                const pinCoords = ol.proj.fromLonLat([lon, lat]);
                locationPinRef.current.setPosition(pinCoords);
                
                console.log(`✅ Location pin positioned at: ${pinCoords}`);
                
                // Center map on location with smooth animation
                const currentZoom = mapInstance.current.getView().getZoom();
                const targetZoom = Math.max(currentZoom, 12);
                
                mapInstance.current.getView().animate({
                    center: pinCoords,
                    zoom: targetZoom,
                    duration: 1200
                });
                
                console.log(`🎯 Map centered on location with zoom ${targetZoom}`);
                
            } else if (locationPinRef.current) {
                // Hide pin if no search location
                console.log("🚫 Hiding location pin");
                locationPinRef.current.setPosition(undefined);
            }
        }, [searchLocation, mapInstance, locationPinRef]);
        
        return null;
    };

    // IMPROVED: Enhanced Flexible Legend
    const FlexibleLegend = ({ legendData }) => {
        if (!legendData || !legendData.categories || legendData.categories.length === 0) {
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
        
        return React.createElement('div', {
            style: legendStyle
        }, [
            // Title with icon
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
            }, Object.entries(legendData.statistics).map(([key, value], index) => 
                React.createElement('div', { key: `stat-${index}` }, 
                    `${key.replace(/_/g, ' ')}: ${value}`)
            ))
        ]);
    };

    // IMPROVED: Smart Statistics Component
    const SmartStatistics = ({ features, legendData, layerType, searchLocation }) => {
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
        
        // Generate smart statistics based on layer type
        const layerTitle = layerType === 'land_use' ? 'Land Use' :
                          layerType === 'buildings' ? 'Buildings' :
                          layerType === 'parcels' ? 'Parcels' :
                          layerType === 'environmental' ? 'Protected Areas' :
                          'Features';
        
        return React.createElement('div', {
            style: statsStyle
        }, [
            React.createElement('div', {
                key: 'title',
                style: { fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#1f2937' }
            }, `📊 ${layerTitle} Analysis`),
            
            React.createElement('div', {
                key: 'count',
                style: { fontSize: '11px', color: '#4b5563', marginBottom: '6px' }
            }, `${features.length} features found`),
            
            // Location info
            searchLocation && React.createElement('div', {
                key: 'location',
                style: { fontSize: '10px', color: '#6b7280', marginBottom: '6px' }
            }, `📍 Near: ${searchLocation.name}`),
            
            // Legend statistics
            legendData && legendData.statistics && Object.entries(legendData.statistics).map(([key, value], index) => {
                if (key === 'total_features') return null;
                
                let label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
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
                    React.createElement('span', { key: 'label' }, label + ':'),
                    React.createElement('span', { key: 'value' }, value)
                ]);
            }).filter(Boolean),
            
            // Layer type indicator
            React.createElement('div', {
                key: 'layer-type',
                style: { 
                    fontSize: '9px', 
                    color: '#9ca3af', 
                    marginTop: '8px', 
                    paddingTop: '6px', 
                    borderTop: '1px solid #e5e7eb',
                    fontStyle: 'italic'
                }
            }, `Source: ${layerType}`)
        ]);
    };

    const App = () => {
        console.log("Initializing INTELLIGENT Map component");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your intelligent PDOK assistant.\n\n🧠 I can analyze your queries and provide spatial data efficiently.\n\n📍 Location pins are automatically plotted when you mention places!\n\nTry asking:\n"Show agricultural land in Utrecht province"\n"Buildings near Amsterdam Centraal"\n"Large parcels in Groningen"',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        
        // IMPROVED: Enhanced state for intelligent features
        const [searchLocation, setSearchLocation] = useState(null);
        const [legendData, setLegendData] = useState(null);
        const [layerType, setLayerType] = useState(null);
        const [processingStatus, setProcessingStatus] = useState('ready');
        
        // Refs
        const mapRef = useRef(null);
        const mapInstance = useRef(null);
        const overlayRef = useRef(null);
        const messagesEndRef = useRef(null);
        const locationPinRef = useRef(null);

        // Auto-scroll messages
        const scrollToBottom = () => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        };

        useEffect(() => {
            scrollToBottom();
        }, [messages]);

        // IMPROVED: Debug state changes
        useEffect(() => {
            console.log("🔄 Intelligent state update:", {
                features: features.length,
                searchLocation: searchLocation?.name,
                legendData: !!legendData,
                layerType,
                processingStatus
            });
        }, [features, searchLocation, legendData, layerType, processingStatus]);

        // Initialize OpenLayers map
        useEffect(() => {
            console.log("🗺️ Setting up intelligent OpenLayers map");
            
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

                mapInstance.current = new ol.Map({
                    target: mapRef.current,
                    layers: [osmLayer, satelliteLayer],
                    view: new ol.View({
                        center: ol.proj.fromLonLat(mapCenter),
                        zoom: mapZoom
                    }),
                    controls: [
                        new ol.control.Zoom(),
                        new ol.control.Attribution()
                    ]
                });

                // Map event listeners
                mapInstance.current.getView().on('change:center', () => {
                    const center = ol.proj.toLonLat(mapInstance.current.getView().getCenter());
                    setMapCenter(center);
                });

                mapInstance.current.getView().on('change:resolution', () => {
                    const zoom = mapInstance.current.getView().getZoom();
                    setMapZoom(Math.round(zoom));
                });

                // Popup setup
                const popupContainer = document.createElement('div');
                popupContainer.className = 'ol-popup';
                const popupContent = document.createElement('div');
                popupContent.id = 'popup-content';
                popupContainer.appendChild(popupContent);
                const popupCloser = document.createElement('a');
                popupCloser.className = 'ol-popup-closer';
                popupCloser.href = '#';
                popupCloser.innerHTML = '×';
                popupContainer.appendChild(popupCloser);

                overlayRef.current = new ol.Overlay({
                    element: popupContainer,
                    autoPan: {
                        animation: { duration: 250 }
                    }
                });
                mapInstance.current.addOverlay(overlayRef.current);

                // IMPROVED: Initialize location pin overlay
                locationPinRef.current = new ol.Overlay({
                    positioning: 'bottom-center',
                    stopEvent: false,
                    offset: [0, -10]
                });
                mapInstance.current.addOverlay(locationPinRef.current);

                popupCloser.onclick = () => {
                    overlayRef.current.setPosition(undefined);
                    popupCloser.blur();
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
                        const name = feature.get('name') || 'Feature';
                        const description = feature.get('description') || '';
                        const lonLat = ol.proj.toLonLat(coordinates);
                        
                        // Intelligent popup content based on layer type
                        let popupContent = `
                            <div class="space-y-2">
                                <h3 class="text-sm font-semibold text-gray-800">${name}</h3>
                                <div class="text-xs text-gray-600">
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-1">${description}</p>` : ''}
                                </div>
                            </div>
                        `;
                        
                        document.getElementById('popup-content').innerHTML = popupContent;
                        overlayRef.current.setPosition(coordinates);
                    } else {
                        overlayRef.current.setPosition(undefined);
                    }
                });

                console.log("✅ Intelligent map setup complete");

                return () => {
                    if (mapInstance.current) {
                        mapInstance.current.setTarget(null);
                    }
                };
            } catch (error) {
                console.error("❌ Error setting up map:", error);
            }
        }, [mapView]);

        // Switch map views
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

        // IMPROVED: Intelligent query handling
        const handleQuery = async () => {
            if (!query.trim()) return;
            
            const userMessage = {
                type: 'user',
                content: query,
                timestamp: new Date()
            };
            
            setMessages(prev => [...prev, userMessage]);
            setIsLoading(true);
            setProcessingStatus('analyzing');
            const currentQuery = query;
            setQuery('');

            try {
                console.log("🧠 Sending intelligent query:", currentQuery);
                
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: currentQuery
                    })
                });
                
                const data = await res.json();
                console.log("🎯 Received intelligent response:", data);
                
                setProcessingStatus('processing');
                
                let responseContent = '';
                let foundFeatures = false;
                
                if (data && typeof data === 'object') {
                    responseContent = data.response || data.message || 'Analysis completed.';
                    
                    // Extract and validate features
                    const geojsonData = data.geojson_data || [];
                    console.log(`📦 Processing ${geojsonData.length} features`);
                    
                    // Validate features
                    const validFeatures = geojsonData.filter(feature => {
                        return feature && 
                               typeof feature === 'object' && 
                               'lat' in feature && 
                               'lon' in feature && 
                               feature.lat !== 0 && 
                               feature.lon !== 0 &&
                               feature.lat >= 50 && feature.lat <= 54 &&
                               feature.lon >= 3 && feature.lon <= 8;
                    });
                    
                    console.log(`✅ ${validFeatures.length} valid features after validation`);
                    
                    if (validFeatures.length > 0) {
                        setFeatures(validFeatures);
                        setLayerType(data.layer_type || 'unknown');
                        setLegendData(data.legend_data);
                        setProcessingStatus('success');
                        foundFeatures = true;
                        
                        // Update map with features
                        updateMapFeatures(validFeatures, data.layer_type);
                    }
                    
                    // IMPROVED: Always handle search location
                    const backendSearchLocation = data.search_location;
                    if (backendSearchLocation && 
                        backendSearchLocation.lat && 
                        backendSearchLocation.lon &&
                        backendSearchLocation.lat !== 0 && 
                        backendSearchLocation.lon !== 0) {
                        
                        console.log("📍 Setting search location from backend:", backendSearchLocation);
                        setSearchLocation(backendSearchLocation);
                    } else {
                        // Try to extract location from query text
                        console.log("🔍 Trying to extract location from response");
                        const extractedLocation = extractLocationFromQuery(currentQuery, validFeatures);
                        if (extractedLocation) {
                            console.log("📍 Setting extracted location:", extractedLocation);
                            setSearchLocation(extractedLocation);
                        }
                    }
                    
                } else if (data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                    setProcessingStatus('error');
                } else {
                    setProcessingStatus('completed');
                }
                
                const assistantMessage = {
                    type: 'assistant',
                    content: responseContent,
                    timestamp: new Date()
                };
                
                setMessages(prev => [...prev, assistantMessage]);
                
            } catch (error) {
                console.error("❌ Intelligent query error:", error);
                setProcessingStatus('error');
                
                const errorMessage = {
                    type: 'assistant',
                    content: `Sorry, I encountered an error: ${error.message}`,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, errorMessage]);
            } finally {
                setIsLoading(false);
                setTimeout(() => setProcessingStatus('ready'), 2000);
            }
        };

        // IMPROVED: Extract location from query text as fallback
        const extractLocationFromQuery = (queryText, features) => {
            const locationPatterns = [
                /(?:in|near|around|at)\s+([A-Za-z][A-Za-z\s]+?)(?:\s|$|,|\.|province)/i,
                /([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:province|area|city)/i
            ];
            
            for (const pattern of locationPatterns) {
                const match = queryText.match(pattern);
                if (match) {
                    const locationName = match[1].trim();
                    
                    // If we have features, use their centroid
                    if (features && features.length > 0) {
                        const lats = features.map(f => f.lat).filter(lat => lat);
                        const lons = features.map(f => f.lon).filter(lon => lon);
                        
                        if (lats.length > 0 && lons.length > 0) {
                            return {
                                lat: lats.reduce((a, b) => a + b) / lats.length,
                                lon: lons.reduce((a, b) => a + b) / lons.length,
                                name: locationName,
                                source: 'query_extraction'
                            };
                        }
                    }
                }
            }
            
            return null;
        };

        // Update map features with intelligent styling
        const updateMapFeatures = (data, dataLayerType) => {
            if (!mapInstance.current) {
                console.error("❌ Map instance not available");
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
                        console.warn(`⚠️ Skipping feature ${index + 1}: invalid data`);
                        return;
                    }
                    
                    let geom;
                    try {
                        // Process geometry
                        let processedGeometry = JSON.parse(JSON.stringify(f.geometry));
                        
                        geom = new ol.format.GeoJSON().readGeometry(processedGeometry, {
                            dataProjection: 'EPSG:4326',
                            featureProjection: 'EPSG:3857'
                        });
                        
                    } catch (geomError) {
                        console.warn(`⚠️ Geometry error for feature ${index + 1}, using point:`, geomError);
                        geom = new ol.geom.Point(ol.proj.fromLonLat([f.lon, f.lat]));
                    }
                    
                    const feature = new ol.Feature({
                        geometry: geom,
                        name: f.name || `Feature ${index + 1}`,
                        description: f.description || '',
                        properties: f.properties || {}
                    });
                    
                    vectorSource.addFeature(feature);
                    featuresAdded++;
                    
                } catch (error) {
                    console.error(`❌ Error processing feature ${index + 1}:`, error);
                }
            });

            console.log(`✅ Added ${featuresAdded}/${data.length} features to map`);

            if (featuresAdded === 0) {
                console.error("❌ No features were successfully added to the map");
                return;
            }

            // Create intelligent styling based on layer type
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => createIntelligentStyle(feature, dataLayerType, legendData)
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("✅ Vector layer added to map");
            
            // Fit to features
            const extent = vectorSource.getExtent();
            if (extent && extent.every(coord => isFinite(coord))) {
                mapInstance.current.getView().fit(extent, { 
                    padding: [50, 50, 50, 50], 
                    maxZoom: 16,
                    duration: 1000
                });
                console.log("🎯 Map view fitted to features");
            }
        };

        // IMPROVED: Intelligent styling function
        const createIntelligentStyle = (feature, layerType, legendData) => {
            const geomType = feature.getGeometry().getType();
            const props = feature.get('properties') || {};
            
            let fillColor = 'rgba(102, 126, 234, 0.7)';
            let strokeColor = '#667eea';
            let strokeWidth = 2;
            
            // Intelligent styling based on layer type
            if (layerType === 'land_use') {
                const landUse = props.bodemgebruik || props.hoofdklasse || 'Unknown';
                
                if (landUse.toLowerCase().includes('agrarisch')) {
                    fillColor = 'rgba(34, 197, 94, 0.7)';
                    strokeColor = '#22c55e';
                } else if (landUse.toLowerCase().includes('bebouwd')) {
                    fillColor = 'rgba(239, 68, 68, 0.7)';
                    strokeColor = '#ef4444';
                } else if (landUse.toLowerCase().includes('bos')) {
                    fillColor = 'rgba(34, 197, 94, 0.8)';
                    strokeColor = '#16a34a';
                } else if (landUse.toLowerCase().includes('water')) {
                    fillColor = 'rgba(59, 130, 246, 0.8)';
                    strokeColor = '#3b82f6';
                }
                
            } else if (layerType === 'buildings') {
                const year = props.bouwjaar;
                if (year) {
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
                
            } else if (layerType === 'parcels') {
                const area = props.kadastraleGrootteWaarde || 0;
                if (area > 0) {
                    const areaHa = area / 10000;
                    if (areaHa > 5) {
                        fillColor = 'rgba(220, 38, 38, 0.6)';
                        strokeColor = '#dc2626';
                    } else if (areaHa > 1) {
                        fillColor = 'rgba(249, 115, 22, 0.6)';
                        strokeColor = '#f97316';
                    } else {
                        fillColor = 'rgba(34, 197, 94, 0.6)';
                        strokeColor = '#22c55e';
                    }
                }
                
            } else if (layerType === 'environmental') {
                fillColor = 'rgba(34, 197, 94, 0.7)';
                strokeColor = '#22c55e';
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
                    stroke: new ol.style.Stroke({ color: strokeColor, width: strokeWidth }),
                    fill: new ol.style.Fill({ color: fillColor })
                });
            }
        };

        // Clear map function
        const clearMap = () => {
            setFeatures([]);
            setLegendData(null);
            setLayerType(null);
            setSearchLocation(null);
            setProcessingStatus('ready');
            
            if (mapInstance.current) {
                const layersToRemove = [];
                mapInstance.current.getLayers().forEach(layer => {
                    if (layer instanceof ol.layer.Vector) {
                        layersToRemove.push(layer);
                    }
                });
                layersToRemove.forEach(layer => {
                    mapInstance.current.removeLayer(layer);
                });
                
                if (locationPinRef.current) {
                    locationPinRef.current.setPosition(undefined);
                }
            }
        };

        // Handle Enter key
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
                
                {/* IMPROVED: Intelligent Location Pin Component */}
                {React.createElement(IntelligentLocationPin, { 
                    searchLocation, 
                    mapInstance, 
                    locationPinRef 
                })}
                
                {/* Map Controls */}
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

                {/* Map Context Info */}
                <div className="absolute top-20 left-4 z-40 map-context-info">
                    <div className="floating-card p-3">
                        <div className="text-sm text-gray-700">
                            <p className="font-medium">🧠 Intelligent Map</p>
                            <p>Zoom: {mapZoom}</p>
                            {searchLocation && (
                                <p className="text-red-600 font-medium">📍 {searchLocation.name}</p>
                            )}
                            {features.length > 0 && (
                                <p className="text-blue-600 font-medium">
                                    {features.length} {layerType || 'Features'}
                                </p>
                            )}
                            <p className={`text-xs ${
                                processingStatus === 'success' ? 'text-green-600' :
                                processingStatus === 'error' ? 'text-red-600' :
                                processingStatus === 'analyzing' ? 'text-yellow-600' :
                                'text-gray-500'
                            }`}>
                                Status: {processingStatus}
                            </p>
                        </div>
                    </div>
                </div>

                {/* IMPROVED: Chat Interface */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-[600px] glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${
                                    processingStatus === 'analyzing' ? 'bg-yellow-400 animate-pulse' :
                                    processingStatus === 'success' ? 'bg-green-400' :
                                    processingStatus === 'error' ? 'bg-red-400' :
                                    'bg-blue-400'
                                }`}></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">🧠 Intelligent Assistant</h2>
                                    <p className="text-sm text-blue-100">
                                        {processingStatus === 'analyzing' ? 'Analyzing query...' :
                                         processingStatus === 'processing' ? 'Fetching data...' :
                                         processingStatus === 'success' ? 'Analysis complete' :
                                         processingStatus === 'error' ? 'Error occurred' :
                                         'Ready for questions'}
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
                                        <p className="text-xs opacity-75 mt-1">🧠 Processing intelligently...</p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* IMPROVED: Input Area with intelligent examples */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    onClick={() => setQuery("Show agricultural land in Utrecht province")}
                                    className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                                >
                                    🌾 Land Use
                                </button>
                                <button
                                    onClick={() => setQuery("Buildings near Amsterdam Centraal station")}
                                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                                >
                                    🏠 Buildings
                                </button>
                                <button
                                    onClick={() => setQuery("Large parcels in Groningen")}
                                    className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
                                >
                                    📐 Parcels
                                </button>
                                <button
                                    onClick={() => setQuery("Protected areas around Rotterdam")}
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
                                    placeholder="Ask about Dutch spatial data... 🧠📍"
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

                {/* IMPROVED: Smart Statistics Component */}
                {React.createElement(SmartStatistics, { 
                    features: features,
                    legendData: legendData,
                    layerType: layerType,
                    searchLocation: searchLocation
                })}

                {/* IMPROVED: Flexible Legend Component */}
                {React.createElement(FlexibleLegend, { 
                    legendData: legendData 
                })}

                {/* IMPROVED: Intelligent Status Indicator */}
                {(features.length > 0 || searchLocation || processingStatus !== 'ready') && (
                    <div style={{
                        position: 'fixed',
                        top: '50%',
                        right: '20px',
                        transform: 'translateY(-50%)',
                        zIndex: 999,
                        backgroundColor: processingStatus === 'success' ? 'rgba(34, 197, 94, 0.1)' : 
                                        processingStatus === 'error' ? 'rgba(239, 68, 68, 0.1)' : 
                                        processingStatus === 'analyzing' ? 'rgba(245, 158, 11, 0.1)' :
                                        'rgba(59, 130, 246, 0.1)',
                        border: `2px solid ${processingStatus === 'success' ? '#22c55e' : 
                                            processingStatus === 'error' ? '#ef4444' : 
                                            processingStatus === 'analyzing' ? '#f59e0b' :
                                            '#3b82f6'}`,
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '11px',
                        color: processingStatus === 'success' ? '#15803d' : 
                               processingStatus === 'error' ? '#dc2626' : 
                               processingStatus === 'analyzing' ? '#d97706' :
                               '#1d4ed8',
                        minWidth: '120px'
                    }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                            {processingStatus === 'success' ? '✅ INTELLIGENT SUCCESS!' : 
                             processingStatus === 'error' ? '❌ ERROR' : 
                             processingStatus === 'analyzing' ? '🧠 ANALYZING...' :
                             processingStatus === 'processing' ? '⚡ FETCHING...' :
                             '🔄 PROCESSING'}
                        </div>
                        <div>📍 Pin: {searchLocation ? '✅' : '❌'}</div>
                        <div>🏷️ Legend: {legendData ? '✅' : '❌'}</div>
                        <div>📊 Features: {features.length > 0 ? '✅' : '❌'}</div>
                        <div>🗺️ Layer: {layerType || 'None'}</div>
                        {features.length > 0 && (
                            <div>{features.length} items</div>
                        )}
                        {searchLocation && (
                            <div style={{ fontSize: '10px', marginTop: '4px', fontStyle: 'italic' }}>
                                📍 {searchLocation.name}
                            </div>
                        )}
                        {legendData && (
                            <div style={{ fontSize: '10px', marginTop: '2px', fontStyle: 'italic' }}>
                                🏷️ {legendData.title}
                            </div>
                        )}
                    </div>
                )}

                {/* IMPROVED: Smart Help Overlay */}
                {!features.length && !isLoading && !searchLocation && processingStatus === 'ready' && (
                    <div style={{
                        position: 'fixed',
                        bottom: '50%',
                        left: '50%',
                        transform: 'translate(-50%, 50%)',
                        zIndex: 998,
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        padding: '24px',
                        borderRadius: '16px',
                        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                        border: '1px solid rgba(0, 0, 0, 0.1)',
                        fontFamily: 'Inter, sans-serif',
                        maxWidth: '420px',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px', color: '#1f2937' }}>
                            🧠 Intelligent PDOK Assistant
                        </div>
                        <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.4', marginBottom: '12px' }}>
                            I analyze your queries intelligently and automatically plot locations!
                        </div>
                        <div style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.3' }}>
                            <strong>🎯 Smart Features:</strong><br/>
                            📍 <strong>Auto Location Pins:</strong> Mention any Dutch place<br/>
                            🧠 <strong>Intelligent Analysis:</strong> I understand what you need<br/>
                            ⚡ <strong>Fast Response:</strong> Maximum 3 tool calls<br/>
                            🏷️ <strong>Dynamic Legends:</strong> Generated for each data type
                        </div>
                        <div style={{ fontSize: '11px', color: '#4b5563', marginTop: '12px', lineHeight: '1.3' }}>
                            <strong>Try saying:</strong><br/>
                            "Show agricultural land in Utrecht province"<br/>
                            "Buildings near Amsterdam Centraal station"<br/>
                            "Large parcels in Groningen"
                        </div>
                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '12px', fontStyle: 'italic' }}>
                            🚀 Powered by intelligent query analysis
                        </div>
                    </div>
                )}

                {/* IMPROVED: Processing Animation Overlay */}
                {isLoading && (
                    <div style={{
                        position: 'fixed',
                        top: '0',
                        left: '0',
                        right: '0',
                        bottom: '0',
                        backgroundColor: 'rgba(0, 0, 0, 0.1)',
                        zIndex: 1000,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        pointerEvents: 'none'
                    }}>
                        <div style={{
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            padding: '20px',
                            borderRadius: '12px',
                            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                            textAlign: 'center',
                            fontFamily: 'Inter, sans-serif'
                        }}>
                            <div style={{
                                fontSize: '16px',
                                fontWeight: 'bold',
                                color: '#1f2937',
                                marginBottom: '8px'
                            }}>
                                🧠 Intelligent Processing
                            </div>
                            <div style={{
                                fontSize: '12px',
                                color: '#6b7280',
                                marginBottom: '12px'
                            }}>
                                {processingStatus === 'analyzing' ? 'Analyzing your query...' :
                                 processingStatus === 'processing' ? 'Fetching spatial data...' :
                                 'Processing intelligently...'}
                            </div>
                            <div className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    console.log("🚀 Rendering INTELLIGENT Production Map-Aware React app");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("❌ Failed to initialize INTELLIGENT React app:", error);
}