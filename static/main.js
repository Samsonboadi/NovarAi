console.log("Loading Map-Aware PDOK Chat Assistant - Fixed Layout");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // Enhanced Area Legend Component
    const AreaLegend = ({ features }) => {
        // Check if we have area data
        const hasAreaData = features.some(f => f.properties?.area_m2 && f.properties.area_m2 > 0);
        
        if (!hasAreaData) return null;
        
        return React.createElement('div', {
            className: "area-legend",
            style: {
                position: 'fixed',
                bottom: '280px', // Position above building age legend
                left: '20px',
                zIndex: 998,
                maxWidth: '250px'
            }
        }, React.createElement('div', {
            className: "floating-card px-3 py-2"
        }, React.createElement('div', {
            className: "text-xs"
        }, [
            React.createElement('p', {
                key: 'title',
                className: "font-medium text-gray-800 mb-2"
            }, "Building Area Legend"),
            React.createElement('div', {
                key: 'legend-items',
                className: "space-y-1"
            }, [
                React.createElement('div', {
                    key: 'large',
                    className: "flex items-center space-x-2"
                }, [
                    React.createElement('div', {
                        key: 'color',
                        className: "w-3 h-3 bg-red-600 rounded"
                    }),
                    React.createElement('span', {
                        key: 'text',
                        className: "text-gray-600"
                    }, "Large (>1000m²)")
                ]),
                React.createElement('div', {
                    key: 'medium',
                    className: "flex items-center space-x-2"
                }, [
                    React.createElement('div', {
                        key: 'color',
                        className: "w-3 h-3 bg-orange-500 rounded"
                    }),
                    React.createElement('span', {
                        key: 'text',
                        className: "text-gray-600"
                    }, "Medium (500-1000m²)")
                ]),
                React.createElement('div', {
                    key: 'standard',
                    className: "flex items-center space-x-2"
                }, [
                    React.createElement('div', {
                        key: 'color',
                        className: "w-3 h-3 bg-yellow-500 rounded"
                    }),
                    React.createElement('span', {
                        key: 'text',
                        className: "text-gray-600"
                    }, "Standard (200-500m²)")
                ]),
                React.createElement('div', {
                    key: 'small',
                    className: "flex items-center space-x-2"
                }, [
                    React.createElement('div', {
                        key: 'color',
                        className: "w-3 h-3 bg-green-500 rounded"
                    }),
                    React.createElement('span', {
                        key: 'text',
                        className: "text-gray-600"
                    }, "Small (<200m²)")
                ])
            ]),
            React.createElement('div', {
                key: 'note',
                className: "mt-2 pt-2 border-t border-gray-200"
            }, React.createElement('p', {
                className: "text-xs text-gray-500"
            }, "Colors show building sizes. Areas from PDOK BAG data."))
        ])));
    };

    // Enhanced Map Statistics Component 
    const EnhancedMapStatistics = ({ features }) => {
        if (features.length === 0) return null;
        
        const years = features
            .map(f => f.properties?.bouwjaar)
            .filter(year => year && !isNaN(year));
        
        const areas = features
            .map(f => f.properties?.area_m2)
            .filter(area => area && area > 0);
        
        const distances = features
            .map(f => f.properties?.distance_km)
            .filter(dist => dist && dist > 0);
        
        return React.createElement('div', {
            className: "map-statistics"
        }, React.createElement('div', {
            className: "floating-card px-4 py-3 max-w-xs"
        }, React.createElement('div', {
            className: "text-sm"
        }, [
            React.createElement('p', {
                key: 'title',
                className: "font-medium text-gray-800 mb-1"
            }, "Search Results"),
            React.createElement('p', {
                key: 'count',
                className: "text-gray-600"
            }, `${features.length} buildings displayed`),
            
            // Area statistics
            ...(areas.length > 0 ? [
                React.createElement('p', {
                    key: 'area-range',
                    className: "text-gray-600"
                }, `Area: ${Math.min(...areas).toLocaleString()}m² - ${Math.max(...areas).toLocaleString()}m²`),
                React.createElement('p', {
                    key: 'area-avg',
                    className: "text-gray-600"
                }, `Avg: ${Math.round(areas.reduce((sum, area) => sum + area, 0) / areas.length).toLocaleString()}m²`)
            ] : []),
            
            // Distance statistics
            ...(distances.length > 0 ? [
                React.createElement('p', {
                    key: 'distance',
                    className: "text-gray-600"
                }, `Distance: ${Math.min(...distances).toFixed(3)}km - ${Math.max(...distances).toFixed(3)}km`)
            ] : []),
            
            // Year statistics
            ...(years.length > 0 ? [
                React.createElement('p', {
                    key: 'years',
                    className: "text-gray-600"
                }, `Built: ${Math.min(...years)} - ${Math.max(...years)}`)
            ] : [])
        ])));
    };

    const App = () => {
        console.log("Initializing Map-Aware React component with fixed layout");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your map-aware AI assistant. I now use proper address-centered search! Try: "Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²"',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        
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
            console.log("Setting up Map-Aware OpenLayers map with fixed controls");
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

                // Create controls array manually to avoid ol.control.defaults issue
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

                // Map movement listeners for context awareness
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

                closer.onclick = () => {
                    overlayRef.current.setPosition(undefined);
                    closer.blur();
                    return false;
                };

                // Enhanced click handler with more details
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
                        } else if (geom.getType() === 'LineString') {
                            const coords = geom.getCoordinates();
                            coordinates = coords[Math.floor(coords.length / 2)];
                        } else {
                            coordinates = geom.getFirstCoordinate();
                        }
                        
                        const props = feature.get('properties') || {};
                        const name = feature.get('name') || 'Unknown Feature';
                        const description = feature.get('description') || '';
                        const lonLat = ol.proj.toLonLat(coordinates);
                        
                        // Enhanced popup with more building details
                        let popupContent = `
                            <div class="space-y-3">
                                <h3 class="text-lg font-semibold text-gray-800">${name}</h3>
                                <div class="text-sm text-gray-600">
                                    <p><span class="font-medium">Type:</span> ${geom.getType()}</p>
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-2">${description}</p>` : ''}
                        `;
                        
                        // Add building-specific information
                        if (props.bouwjaar) {
                            const year = props.bouwjaar;
                            let era = 'Unknown';
                            if (year < 1900) era = 'Historic (pre-1900)';
                            else if (year < 1950) era = 'Early Modern (1900-1950)';
                            else if (year < 2000) era = 'Mid-Century (1950-2000)';
                            else era = 'Contemporary (2000+)';
                            
                            popupContent += `<p><span class="font-medium">Built:</span> ${year} (${era})</p>`;
                        }
                        
                        if (props.area_m2) {
                            popupContent += `<p><span class="font-medium">Area:</span> ${Math.round(props.area_m2).toLocaleString()}m²</p>`;
                        }
                        
                        if (props.aantal_verblijfsobjecten) {
                            popupContent += `<p><span class="font-medium">Units:</span> ${props.aantal_verblijfsobjecten}</p>`;
                        }
                        
                        popupContent += '</div>';
                        
                        // Show additional properties
                        if (Object.keys(props).length > 0) {
                            popupContent += '<div class="mt-3 pt-3 border-t border-gray-200"><h4 class="font-medium text-gray-700 mb-2">Additional Properties:</h4>';
                            Object.entries(props).forEach(([key, value]) => {
                                if (value !== null && value !== undefined && 
                                    !['bouwjaar', 'area_m2', 'aantal_verblijfsobjecten', 'centroid_lat', 'centroid_lon'].includes(key)) {
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

        // Enhanced chat query handler with new combined response format
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
                
                // Send map context along with query
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
                console.log("Data type:", typeof data);
                
                let responseContent = '';
                let foundBuildings = false;
                
                // NEW: Handle combined response format (text + geojson)
                if (data && typeof data === 'object' && 'response' in data && 'geojson_data' in data) {
                    console.log("✅ Detected combined response format");
                    
                    responseContent = data.response;
                    const geojsonData = data.geojson_data;
                    
                    if (Array.isArray(geojsonData) && geojsonData.length > 0) {
                        const firstItem = geojsonData[0];
                        
                        // Validate building data
                        if (firstItem && typeof firstItem === 'object' && 
                            'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 
                            'geometry' in firstItem && firstItem.lat !== 0 && firstItem.lon !== 0) {
                            
                            console.log("✓ Valid building data in combined response - updating map");
                            setFeatures(geojsonData);
                            updateMapFeatures(geojsonData);
                            foundBuildings = true;
                        }
                    }
                }
                // Handle legacy array format (buildings only)
                else if (Array.isArray(data) && data.length > 0) {
                    const firstItem = data[0];
                    console.log("First item:", firstItem);
                    
                    // Check if this is building data with geometry
                    if (firstItem && typeof firstItem === 'object' && 
                        'name' in firstItem && 'lat' in firstItem && 'lon' in firstItem && 
                        'geometry' in firstItem && firstItem.lat !== 0 && firstItem.lon !== 0) {
                        
                        console.log("✓ Detected legacy building data format - updating map");
                        setFeatures(data);
                        updateMapFeatures(data);
                        foundBuildings = true;
                        
                        // Enhanced response with statistics
                        const totalArea = data.reduce((sum, building) => 
                            sum + (building.properties?.area_m2 || 0), 0);
                        const years = data.filter(b => b.properties?.bouwjaar).map(b => b.properties.bouwjaar);
                        const avgYear = years.length > 0 ? years.reduce((sum, year) => sum + year, 0) / years.length : null;
                        
                        responseContent = `Found ${data.length} buildings! I've displayed them on the map with enhanced visibility. ` +
                            `Total area: ${Math.round(totalArea).toLocaleString()}m². ` +
                            (avgYear ? `Average construction year: ${Math.round(avgYear)}. ` : '') +
                            `Click on any building to see detailed information.`;
                        
                    } else if (firstItem && firstItem.error) {
                        responseContent = `I encountered an issue: ${firstItem.error}`;
                    } else {
                        // Handle array of strings (text responses)
                        responseContent = Array.isArray(data) ? data.join('\n') : JSON.stringify(data, null, 2);
                    }
                }
                // Handle wrapped text responses
                else if (data && data.response) {
                    responseContent = data.response;
                }
                // Handle error responses
                else if (data && data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                }
                // Handle plain string responses
                else if (typeof data === 'string') {
                    responseContent = data;
                }
                // Handle other data types
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

        // Enhanced map features update with better visibility
        const updateMapFeatures = (data) => {
            if (!mapInstance.current) {
                console.error("Map instance not available");
                return;
            }

            console.log(`Updating map with ${data.length} features (enhanced with area styling)`);
            
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
                    console.log(`Processing feature ${index + 1}/${data.length}:`);
                    console.log(`  Name: ${f.name}`);
                    console.log(`  Coordinates: ${f.lat}, ${f.lon}`);
                    console.log(`  Area: ${f.properties?.area_m2 || 'N/A'}m²`);
                    
                    if (!f.geometry || !f.lat || !f.lon) {
                        console.warn(`  Skipping feature ${index + 1}: missing geometry or coordinates`);
                        return;
                    }
                    
                    if (f.lat === 0 && f.lon === 0) {
                        console.warn(`  Skipping feature ${index + 1}: invalid coordinates (0,0)`);
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
                        
                        // Validate coordinate structure
                        if (processedGeometry.type === 'Polygon') {
                            const coords = processedGeometry.coordinates;
                            if (!Array.isArray(coords) || !Array.isArray(coords[0]) || !Array.isArray(coords[0][0])) {
                                throw new Error("Invalid polygon coordinate structure");
                            }
                            
                            const invalidCoords = coords[0].some(coord => 
                                !Array.isArray(coord) || coord.length !== 2 || 
                                typeof coord[0] !== 'number' || typeof coord[1] !== 'number'
                            );
                            
                            if (invalidCoords) {
                                throw new Error("Polygon contains invalid coordinate pairs");
                            }
                            
                        } else if (processedGeometry.type === 'Point') {
                            const coords = processedGeometry.coordinates;
                            if (!Array.isArray(coords) || coords.length !== 2 || 
                                typeof coords[0] !== 'number' || typeof coords[1] !== 'number') {
                                throw new Error("Invalid point coordinate structure");
                            }
                        }
                        
                        geom = new ol.format.GeoJSON().readGeometry(processedGeometry, {
                            dataProjection: 'EPSG:4326',
                            featureProjection: 'EPSG:3857'
                        });
                        
                    } catch (geomError) {
                        console.error(`  Geometry processing error for feature ${index + 1}:`, geomError);
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
                    console.log(`  Successfully added ${geom.getType()} feature ${index + 1} to map`);
                    
                } catch (error) {
                    console.error(`Error processing feature ${index + 1}:`, error);
                }
            });

            console.log(`Total features added to map: ${featuresAdded}/${data.length}`);

            if (featuresAdded === 0) {
                console.error("No features were successfully added to the map");
                return;
            }

            // ENHANCED STYLING WITH AREA-BASED COLORS
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => {
                    const geomType = feature.getGeometry().getType();
                    const props = feature.get('properties') || {};
                    
                    console.log(`Styling ${geomType} feature: ${feature.get('name')}`);
                    
                    if (geomType === 'Point') {
                        // Area-based colors for points
                        const area = props.area_m2 || 0;
                        let pointColor = '#667eea'; // Default blue
                        
                        if (area > 1000) {
                            pointColor = '#dc2626'; // Large: red
                        } else if (area > 500) {
                            pointColor = '#f97316'; // Medium: orange
                        } else if (area > 200) {
                            pointColor = '#eab308'; // Standard: yellow
                        } else if (area > 0) {
                            pointColor = '#22c55e'; // Small: green
                        }
                        
                        return new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 12,  // Larger for visibility
                                fill: new ol.style.Fill({ color: pointColor }),
                                stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 })
                            })
                        });
                        
                    } else if (geomType === 'Polygon') {
                        const year = props.bouwjaar;
                        const area = props.area_m2 || 0;
                        
                        let fillColor = 'rgba(102, 126, 234, 0.7)'; // Default blue
                        let strokeColor = '#667eea';
                        
                        // PRIORITY 1: Color by area if available and user searched by area
                        if (area > 0) {
                            if (area > 1000) {
                                fillColor = 'rgba(220, 38, 38, 0.8)';    // Large buildings: red
                                strokeColor = '#dc2626';
                            } else if (area > 500) {
                                fillColor = 'rgba(249, 115, 22, 0.8)';   // Medium buildings: orange
                                strokeColor = '#f97316';
                            } else if (area > 200) {
                                fillColor = 'rgba(234, 179, 8, 0.8)';    // Standard buildings: yellow
                                strokeColor = '#eab308';
                            } else {
                                fillColor = 'rgba(34, 197, 94, 0.8)';    // Small buildings: green
                                strokeColor = '#22c55e';
                            }
                        }
                        // FALLBACK: Color by age if no area data
                        else if (year) {
                            if (year < 1900) {
                                fillColor = 'rgba(139, 0, 0, 0.7)';      // Historic: dark red
                                strokeColor = '#8B0000';
                            } else if (year < 1950) {
                                fillColor = 'rgba(255, 69, 0, 0.7)';     // Early modern: orange
                                strokeColor = '#FF4500';
                            } else if (year < 2000) {
                                fillColor = 'rgba(50, 205, 50, 0.7)';    // Mid-century: green
                                strokeColor = '#32CD32';
                            } else {
                                fillColor = 'rgba(30, 144, 255, 0.7)';   // Modern: blue
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
                        
                    } else if (geomType === 'LineString') {
                        return new ol.style.Style({
                            stroke: new ol.style.Stroke({ 
                                color: '#667eea', 
                                width: 4
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
            console.log("Enhanced area-based styling vector layer added to map");
            
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
                            <p className="font-medium">Map Context</p>
                            <p>Center: {mapCenter[1].toFixed(4)}°N, {mapCenter[0].toFixed(4)}°E</p>
                            <p>Zoom: {mapZoom}</p>
                            {features.length > 0 && (
                                <p className="text-blue-600 font-medium">{features.length} features loaded</p>
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
                                    <h2 className="text-lg font-semibold text-white">Map Aware Agentic mapper </h2>
                                    <p className="text-sm text-blue-100">Intelligent Agent Mapping System</p>
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
                                        <p className="text-xs opacity-75 mt-1">FIXED agent processing...</p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Enhanced Input Area with FIXED prompts */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    onClick={() => setQuery("Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²")}
                                    className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                                >
                                    Address Search
                                </button>
                                <button
                                    onClick={() => setQuery("Find buildings near Amsterdam Centraal larger than 500m²")}
                                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                                >
                                    Station Area
                                </button>
                                <button
                                    onClick={() => setQuery("Show historic buildings near Groningen station built before 1950")}
                                    className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
                                >
                                    Historic Search
                                </button>
                                <button
                                    onClick={() => setQuery("What's fixed in the new address-centered search?")}
                                    className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded-full hover:bg-orange-200 transition-colors"
                                >
                                    What's Fixed?
                                </button>
                            </div>
                            
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    className="flex-1 search-input rounded-xl px-4 py-2 text-sm focus:outline-none"
                                    placeholder="Try: 'buildings near [address] with area > 300m²' - now FIXED!"
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
                            {/* FIXED indicator */}
                            <div className="absolute -bottom-3 -right-3 bg-green-500 text-white text-xs rounded-full px-2 py-1 font-bold">
                                AGENT
                            </div>
                        </div>
                    </button>
                )}

                {/* REPLACE YOUR OLD MAP STATISTICS WITH THIS: */}
                {React.createElement(EnhancedMapStatistics, { features: features })}

                {/* ADD THE NEW AREA LEGEND: */}
                {React.createElement(AreaLegend, { features: features })}

                {/* KEEP YOUR EXISTING BUILDING AGE LEGEND: */}
                {features.some(f => f.properties?.bouwjaar) && (
                    <div className="building-legend">
                        <div className="floating-card px-3 py-2">
                            <div className="text-xs">
                                <p className="font-medium text-gray-800 mb-2">Building Age Legend</p>
                                <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-red-800 rounded"></div>
                                        <span className="text-gray-600">Historic (pre-1900)</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-orange-500 rounded"></div>
                                        <span className="text-gray-600">Early Modern (1900-1950)</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-green-500 rounded"></div>
                                        <span className="text-gray-600">Mid-Century (1950-2000)</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <div className="w-3 h-3 bg-blue-500 rounded"></div>
                                        <span className="text-gray-600">Contemporary (2000+)</span>
                                    </div>
                                </div>
                                <div className="mt-2 pt-2 border-t border-gray-200">
                                    <p className="text-xs text-gray-500">
                                        {features.some(f => f.properties?.area_m2 > 0) 
                                            ? "Showing age colors when no area data available" 
                                            : "Colors show building construction periods"
                                        }
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Address Center Indicator (NEW) */}
                {features.length > 0 && features.some(f => f.properties?.distance_km !== undefined) && (
                    <div style={{
                        position: 'fixed',
                        top: '50%',
                        right: '20px',
                        transform: 'translateY(-50%)',
                        zIndex: 999
                    }}>
                        <div className="floating-card px-3 py-2 bg-green-50 border-green-200">
                            <div className="text-xs text-green-800">
                                <p className="font-medium">✅ FIXED!</p>
                                <p>Address-centered search</p>
                                <p>Sorted by distance</p>
                                <p>No random selection</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    console.log("Rendering Map-Aware React app with Fixed Layout");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("Failed to initialize Map-Aware React app:", error);
}