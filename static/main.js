console.log("Loading modern PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    // Create root for React 18
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    const App = () => {
        console.log("Initializing React component");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your AI assistant for exploring Dutch geographic data. Ask me to show buildings, find locations, or explore map features!',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        
        // Refs
        const mapRef = useRef(null);
        const mapInstance = useRef(null);
        const overlayRef = useRef(null);
        const messagesEndRef = useRef(null);

        // Auto-scroll to bottom of messages
        const scrollToBottom = () => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        };

        useEffect(() => {
            scrollToBottom();
        }, [messages]);

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

                mapInstance.current = new ol.Map({
                    target: mapRef.current,
                    layers: [osmLayer, satelliteLayer],
                    view: new ol.View({
                        center: ol.proj.fromLonLat([5.2913, 52.1326]), // Netherlands center
                        zoom: 8
                    })
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

                closer.onclick = () => {
                    overlayRef.current.setPosition(undefined);
                    closer.blur();
                    return false;
                };

                // Click handler for features
                mapInstance.current.on('singleclick', (evt) => {
                    const feature = mapInstance.current.forEachFeatureAtPixel(evt.pixel, f => f);
                    if (feature) {
                        const coordinates = feature.getGeometry().getType() === 'Point' ?
                            feature.getGeometry().getCoordinates() :
                            feature.getGeometry().getFirstCoordinate();
                        const props = feature.get('properties') || {};
                        const name = feature.get('name') || 'Unknown Feature';
                        const description = feature.get('description') || '';
                        const lonLat = ol.proj.toLonLat(coordinates);
                        
                        let popupContent = `
                            <div class="space-y-3">
                                <h3 class="text-lg font-semibold text-gray-800">${name}</h3>
                                <div class="text-sm text-gray-600">
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-2">${description}</p>` : ''}
                                </div>
                        `;
                        
                        if (Object.keys(props).length > 0) {
                            popupContent += '<div class="mt-3 pt-3 border-t border-gray-200"><h4 class="font-medium text-gray-700 mb-2">Properties:</h4>';
                            Object.entries(props).forEach(([key, value]) => {
                                if (value !== null && value !== undefined) {
                                    popupContent += `<p class="text-xs text-gray-600"><span class="font-medium">${key}:</span> ${value}</p>`;
                                }
                            });
                            popupContent += '</div>';
                        }
                        
                        popupContent += '</div>';
                        document.getElementById('popup-content').innerHTML = popupContent;
                        overlayRef.current.setPosition(coordinates);
                    } else {
                        overlayRef.current.setPosition(undefined);
                    }
                });

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

        // Handle chat query
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
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: currentQuery, current_features: features })
                });
                
                const data = await res.json();
                console.log("Received data from backend:", data);
                console.log("Data type:", typeof data);
                console.log("Is array:", Array.isArray(data));
                
                let responseContent;
                
                // Check if we got building data
                if (Array.isArray(data) && data.length > 0) {
                    const firstItem = data[0];
                    console.log("First item:", firstItem);
                    
                    // Check if it's building data (has required fields for mapping)
                    if (firstItem && typeof firstItem === 'object' && 
                        'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 'geometry' in firstItem) {
                        
                        console.log("Detected building data - updating map");
                        setFeatures(data);
                        updateMapFeatures(data);
                        responseContent = `Found ${data.length} buildings! I've displayed them on the map. Click on any building to see more details.`;
                        
                    } else if (firstItem && firstItem.error) {
                        responseContent = `I encountered an issue: ${firstItem.error}`;
                    } else {
                        // Data doesn't have building format - show as text
                        responseContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
                    }
                } else if (data && data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                } else {
                    responseContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
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

        // Update map with features
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
                console.log("Removed existing vector layer");
            });

            if (!data || data.length === 0) {
                console.log("No data to display on map");
                return;
            }

            const vectorSource = new ol.source.Vector();
            let featuresAdded = 0;
            
            data.forEach((f, index) => {
                try {
                    console.log(`Processing feature ${index + 1}/${data.length}:`);
                    console.log(`  Name: ${f.name}`);
                    console.log(`  Coordinates: ${f.lat}, ${f.lon}`);
                    console.log(`  Geometry type: ${f.geometry?.type}`);
                    
                    if (!f.geometry || !f.lat || !f.lon) {
                        console.warn(`  Skipping feature ${index + 1}: missing geometry or coordinates`);
                        return;
                    }
                    
                    // Validate coordinates
                    if (f.lat === 0 && f.lon === 0) {
                        console.warn(`  Skipping feature ${index + 1}: invalid coordinates (0,0)`);
                        return;
                    }
                    
                    let geom;
                    try {
                        // Handle tuple coordinates (convert to array)
                        let processedGeometry = { ...f.geometry };
                        
                        if (processedGeometry.coordinates) {
                            // Recursive function to convert all tuples/iterables to arrays
                            function convertTuplesToArrays(obj) {
                                if (typeof obj === 'object' && obj !== null) {
                                    if (Array.isArray(obj)) {
                                        return obj.map(convertTuplesToArrays);
                                    } else if (obj[Symbol.iterator] && typeof obj !== 'string') {
                                        // Convert iterable (including tuples) to array
                                        return Array.from(obj).map(convertTuplesToArrays);
                                    } else if (typeof obj === 'object') {
                                        // Handle objects
                                        const result = {};
                                        for (let key in obj) {
                                            result[key] = convertTuplesToArrays(obj[key]);
                                        }
                                        return result;
                                    }
                                }
                                return obj;
                            }
                            
                            processedGeometry.coordinates = convertTuplesToArrays(processedGeometry.coordinates);
                        }
                        
                        console.log(`  Original geometry:`, f.geometry);
                        console.log(`  Processed geometry:`, processedGeometry);
                        
                        // Validate that we have proper coordinate arrays
                        if (processedGeometry.type === 'Polygon' && processedGeometry.coordinates) {
                            const coords = processedGeometry.coordinates;
                            if (Array.isArray(coords) && Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
                                console.log(`  Valid polygon with ${coords[0].length} points`);
                            } else {
                                console.warn(`  Invalid polygon coordinate structure`);
                                throw new Error("Invalid polygon coordinates");
                            }
                        }
                        
                        geom = new ol.format.GeoJSON().readGeometry(processedGeometry, {
                            dataProjection: 'EPSG:4326',
                            featureProjection: 'EPSG:3857'
                        });
                        
                        console.log(`  OpenLayers geometry created: ${geom.getType()} with ${geom.getCoordinates ? 'coordinates' : 'geometry'}`);
                        
                    } catch (geomError) {
                        console.error(`  Geometry processing error for feature ${index + 1}:`, geomError);
                        console.log(`  Raw geometry data:`, f.geometry);
                        console.log(`  Falling back to point geometry at ${f.lat}, ${f.lon}`);
                        
                        // Fallback to point geometry
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
                    console.log(`  Successfully added feature ${index + 1} to map`);
                    
                } catch (error) {
                    console.error(`Error processing feature ${index + 1}:`, error);
                    console.log(`Feature data:`, f);
                }
            });

            console.log(`Total features added to map: ${featuresAdded}/${data.length}`);

            if (featuresAdded === 0) {
                console.error("No features were successfully added to the map");
                return;
            }

            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => {
                    const geomType = feature.getGeometry().getType();
                    console.log(`Styling ${geomType} feature: ${feature.get('name')}`);
                    
                    if (geomType === 'Point') {
                        return new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 8,
                                fill: new ol.style.Fill({ color: '#667eea' }),
                                stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                            })
                        });
                    } else {
                        // Polygon or other geometry
                        return new ol.style.Style({
                            stroke: new ol.style.Stroke({ color: '#667eea', width: 2 }),
                            fill: new ol.style.Fill({ color: 'rgba(102, 126, 234, 0.2)' })
                        });
                    }
                }
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("Vector layer added to map");
            
            // Fit to features
            const extent = vectorSource.getExtent();
            console.log("Features extent:", extent);
            
            if (extent && extent.some(coord => isFinite(coord))) {
                mapInstance.current.getView().fit(extent, { 
                    padding: [50, 50, 50, 50], 
                    maxZoom: 15,
                    duration: 1000
                });
                console.log("Map view fitted to features");
            } else {
                console.error("Invalid extent, cannot fit map view");
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
                
                {/* Map Controls */}
                <div className="map-controls">
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

                {/* Chat Interface */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-96 glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse-slow"></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">AI Map Assistant</h2>
                                    <p className="text-sm text-blue-100">Ready to help you explore</p>
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
                                        <p>{message.content}</p>
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
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    className="flex-1 search-input rounded-xl px-4 py-2 text-sm focus:outline-none"
                                    placeholder="Ask me about buildings, locations..."
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
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
                        </div>
                    </button>
                )}

                {/* Feature Count Badge */}
                {features.length > 0 && (
                    <div className="fixed bottom-20 left-6 floating-card px-3 py-2 z-40">
                        <p className="text-sm font-medium text-gray-700">
                            {features.length} features on map
                        </p>
                    </div>
                )}
            </div>
        );
    };

    console.log("Rendering React app");
    
    // Render the app using React 18 createRoot or fallback to React 17
    if (root) {
        root.render(<App />);
    } else {
        ReactDOM.render(<App />, container);
    }
    
} catch (error) {
    console.error("Failed to initialize React app:", error);
}