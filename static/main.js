
console.log("Loading INTELLIGENT Production Map-Aware PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // Dynamic Legend Component
    const DynamicLegend = ({ layerType, features }) => {
        if (!layerType || !features || features.length === 0) {
            return null;
        }

        const legendStyle = {
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            zIndex: 998,
            maxWidth: '250px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '10px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(5px)'
        };

        let title = '';
        let categories = [];

        if (layerType === 'buildings' || layerType === 'bag') {
            title = '🏠 Buildings by Age';
            categories = [
                { label: 'Historic (< 1900)', color: '#8B0000' },
                { label: 'Pre-war (1900-1949)', color: '#FF4500' },
                { label: 'Post-war (1950-1979)', color: '#32CD32' },
                { label: 'Late 20th C (1980-1999)', color: '#1E90FF' },
                { label: 'Modern (2000+)', color: '#FF1493' },
                { label: 'Unknown Age', color: '#808080' }
            ];
        } else if (layerType === 'cadastral' || layerType === 'parcels') {
            title = '📐 Parcels by Size';
            categories = [
                { label: 'Large (>5 ha)', color: '#dc2626' },
                { label: 'Medium (1-5 ha)', color: '#f97316' },
                { label: 'Small (<1 ha)', color: '#22c55e' }
            ];
        } else if (layerType === 'bestandbodemgebruik' || layerType === 'land_use') {
            title = '🌾 Land Use Types';
            categories = [
                { label: 'Agricultural', color: '#22c55e' },
                { label: 'Built-up', color: '#ef4444' },
                { label: 'Forest', color: '#16a34a' },
                { label: 'Water', color: '#3b82f6' }
            ];
        } else if (layerType === 'natura2000' || layerType === 'environmental') {
            title = '🌿 Protected Areas';
            categories = [
                { label: 'Nature Reserve', color: '#22c55e' }
            ];
        } else {
            title = '📊 Features';
            categories = [
                { label: 'Features', color: '#3b82f6' }
            ];
        }

        return React.createElement('div', {
            style: legendStyle
        }, [
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
            }, title),
            ...categories.map((category, index) => 
                React.createElement('div', {
                    key: `category-${index}`,
                    style: { 
                        fontSize: '10px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        marginBottom: '4px'
                    }
                }, [
                    React.createElement('div', {
                        key: 'color',
                        style: { 
                            width: '14px', 
                            height: '14px', 
                            backgroundColor: category.color, 
                            marginRight: '8px', 
                            borderRadius: '2px',
                            border: '1px solid rgba(0,0,0,0.2)',
                            flexShrink: 0
                        }
                    }),
                    React.createElement('span', { 
                        key: 'label', 
                        style: { 
                            color: '#4b5563', 
                            fontSize: '10px',
                            lineHeight: '1.2',
                            fontWeight: '500'
                        } 
                    }, category.label)
                ])
            )
        ]);
    };

    // Intelligent Location Pin Component
    const IntelligentLocationPin = ({ searchLocation, mapInstance, locationPinRef }) => {
        useEffect(() => {
            console.log("🔍 IntelligentLocationPin effect:", searchLocation);
            
            if (searchLocation && locationPinRef.current && mapInstance.current) {
                console.log(`📍 Creating location pin: ${searchLocation.name} at ${searchLocation.lat}, ${searchLocation.lon}`);
                
                const lat = parseFloat(searchLocation.lat);
                const lon = parseFloat(searchLocation.lon);
                
                if (isNaN(lat) || isNaN(lon)) {
                    console.error("❌ Invalid coordinates for location pin:", searchLocation);
                    return;
                }
                
                if (lat < 50.5 || lat > 53.8 || lon < 3.0 || lon > 7.5) {
                    console.warn("⚠️ Coordinates outside Netherlands bounds:", lat, lon);
                }
                
                const pinContainer = document.createElement('div');
                pinContainer.style.cssText = `
                    pointer-events: none;
                    z-index: 1001;
                    position: relative;
                `;
                
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
                
                locationPinRef.current.setElement(pinContainer);
                
                const pinCoords = ol.proj.fromLonLat([lon, lat]);
                locationPinRef.current.setPosition(pinCoords);
                
                console.log(`✅ Location pin positioned at: ${pinCoords}`);
                
                const currentZoom = mapInstance.current.getView().getZoom();
                const targetZoom = Math.max(currentZoom, 12);
                
                mapInstance.current.getView().animate({
                    center: pinCoords,
                    zoom: targetZoom,
                    duration: 1200
                });
                
                console.log(`🎯 Map centered on location with zoom ${targetZoom}`);
                
            } else if (locationPinRef.current) {
                console.log("🚫 Hiding location pin");
                locationPinRef.current.setPosition(undefined);
            }
        }, [searchLocation, mapInstance, locationPinRef]);
        
        return null;
    };

    const App = () => {
        console.log("Initializing INTELLIGENT Map component");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your intelligent PDOK assistant.\n\n🧠 I can analyze your queries and provide spatial data efficiently.\n\nTry asking:\n"Show buildings near Groningen"\n"Agricultural land in Utrecht province"\n"Large parcels in Amsterdam"',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        const [layerType, setLayerType] = useState(null);
        const [searchLocation, setSearchLocation] = useState(null);
        
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

        // Initialize OpenLayers map
        useEffect(() => {
            console.log("🗺️ Setting up intelligent OpenLayers map");
            
            try {
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

                mapInstance.current.getView().on('change:center', () => {
                    const center = ol.proj.toLonLat(mapInstance.current.getView().getCenter());
                    setMapCenter(center);
                });

                mapInstance.current.getView().on('change:resolution', () => {
                    const zoom = mapInstance.current.getView().getZoom();
                    setMapZoom(Math.round(zoom));
                });

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
                        
                        let popupContent = `
                            <div class="space-y-2">
                                <h3 class="text-sm font-semibold text-gray-800">${name}</h3>
                                <div class="text-xs text-gray-600">
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-1">${description}</p>` : ''}
                        `;
                        
                        if (layerType === 'buildings' || layerType === 'bag') {
                            if (props.bouwjaar) {
                                const year = parseInt(props.bouwjaar);
                                const age = new Date().getFullYear() - year;
                                let ageCategory = '';
                                
                                if (year < 1900) ageCategory = 'Historic';
                                else if (year < 1950) ageCategory = 'Pre-war';
                                else if (year < 1980) ageCategory = 'Post-war';
                                else if (year < 2000) ageCategory = 'Late 20th Century';
                                else ageCategory = 'Modern';
                                
                                popupContent += `<p><span class="font-medium">Built:</span> ${year} (${age} years old, ${ageCategory})</p>`;
                            }
                            
                            if (props.oppervlakte) {
                                popupContent += `<p><span class="font-medium">Floor area:</span> ${props.oppervlakte}m²</p>`;
                            }
                            
                            if (props.status) {
                                popupContent += `<p><span class="font-medium">Status:</span> ${props.status}</p>`;
                            }
                        } else if (layerType === 'cadastral' || layerType === 'parcels') {
                            if (props.kadastraleGrootteWaarde) {
                                const areaM2 = parseFloat(props.kadastraleGrootteWaarde);
                                const areaHa = areaM2 / 10000;
                                popupContent += `<p><span class="font-medium">Area:</span> ${areaM2.toFixed(0)} m² (${areaHa.toFixed(2)} ha)</p>`;
                            }
                            
                            if (props.perceelnummer) {
                                popupContent += `<p><span class="font-medium">Parcel Number:</span> ${props.perceelnummer}</p>`;
                            }
                            
                            if (props.kadastraleGemeenteWaarde) {
                                popupContent += `<p><span class="font-medium">Municipality:</span> ${props.kadastraleGemeenteWaarde}</p>`;
                            }
                            
                            if (props.sectie) {
                                popupContent += `<p><span class="font-medium">Section:</span> ${props.sectie}</p>`;
                            }
                        } else if (layerType === 'bestandbodemgebruik' || layerType === 'land_use') {
                            if (props.bodemgebruik) {
                                popupContent += `<p><span class="font-medium">Land Use:</span> ${props.bodemgebruik}</p>`;
                            }
                        } else if (layerType === 'natura2000' || layerType === 'environmental') {
                            if (props.naam) {
                                popupContent += `<p><span class="font-medium">Name:</span> ${props.naam}</p>`;
                            }
                        }
                        
                        popupContent += `
                                </div>
                            </div>
                        `;
                        
                        document.getElementById('popup-content').innerHTML = popupContent;
                        overlayRef.current.setPosition(coordinates);
                    } else {
                        overlayRef.current.setPosition(undefined);
                    }
                });

                console.log("✅ intelligent map setup complete");

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

        // Intelligent building styling function
        const createIntelligentStyle = (feature, layerType) => {
            const geomType = feature.getGeometry().getType();
            const props = feature.get('properties') || {};
            
            let fillColor = 'rgba(102, 126, 234, 0.7)';
            let strokeColor = '#667eea';
            let strokeWidth = 2;
            
            if (layerType === 'buildings' || layerType === 'bag') {
                const year = props.bouwjaar;
                if (year && !isNaN(parseInt(year))) {
                    const buildingYear = parseInt(year);
                    
                    if (buildingYear < 1900) {
                        fillColor = 'rgba(139, 0, 0, 0.8)';
                        strokeColor = '#8B0000';
                    } else if (buildingYear < 1950) {
                        fillColor = 'rgba(255, 69, 0, 0.8)';
                        strokeColor = '#FF4500';
                    } else if (buildingYear < 1980) {
                        fillColor = 'rgba(50, 205, 50, 0.8)';
                        strokeColor = '#32CD32';
                    } else if (buildingYear < 2000) {
                        fillColor = 'rgba(30, 144, 255, 0.8)';
                        strokeColor = '#1E90FF';
                    } else {
                        fillColor = 'rgba(255, 20, 147, 0.8)';
                        strokeColor = '#FF1493';
                    }
                } else {
                    fillColor = 'rgba(128, 128, 128, 0.7)';
                    strokeColor = '#808080';
                }
            } else if (layerType === 'land_use' || layerType === 'bestandbodemgebruik') {
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
            } else if (layerType === 'parcels' || layerType === 'cadastral') {
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
            } else if (layerType === 'environmental' || layerType === 'natura2000') {
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

        // Extract location from query text as fallback
        const extractLocationFromQuery = (queryText, features) => {
            const locationPatterns = [
                /(?:in|near|around|at)\s+([A-Za-z][A-Za-z\s]+?)(?:\s|$|,|\.|province)/i,
                /([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:province|area|city)/i,
                /([A-Za-z]+)(?:\s|$)/i
            ];
            
            for (const pattern of locationPatterns) {
                const match = queryText.match(pattern);
                if (match) {
                    const locationName = match[1].trim();
                    
                    if (features && features.length > 0) {
                        const validFeatures = features.filter(f => 
                            f.lat >= 50.5 && f.lat <= 53.8 && 
                            f.lon >= 3.0 && f.lon <= 7.5
                        );
                        
                        if (validFeatures.length > 0) {
                            const lats = validFeatures.map(f => f.lat);
                            const lons = validFeatures.map(f => f.lon);
                            
                            return {
                                lat: lats.reduce((a, b) => a + b) / lats.length,
                                lon: lons.reduce((a, b) => a + b) / lons.length,
                                name: locationName,
                                source: 'query_extraction'
                            };
                        }
                    }
                    break;
                }
            }
            
            return null;
        };

        // Updated query handling to include search location
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
                console.log("🧠 Sending query:", currentQuery);
                
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: currentQuery
                    })
                });
                
                const data = await res.json();
                console.log("🎯 Received response:", data);
                
                let responseContent = '';
                let foundFeatures = false;
                
                if (data && typeof data === 'object') {
                    responseContent = data.response || data.message || 'Analysis completed.';
                    
                    const geojsonData = data.geojson_data || [];
                    console.log(`📦 Processing ${geojsonData.length} features`);
                    
                    const validFeatures = geojsonData.filter(feature => {
                        return feature && 
                               typeof feature === 'object' && 
                               'lat' in feature && 
                               'lon' in feature && 
                               feature.lat !== 0 && 
                               feature.lon !== 0 &&
                               feature.lat >= 50.5 && feature.lat <= 53.8 &&
                               feature.lon >= 3.0 && feature.lon <= 7.5;
                    });
                    
                    console.log(`✅ ${validFeatures.length} valid features after validation`);
                    
                    if (validFeatures.length > 0) {
                        setFeatures(validFeatures);
                        setLayerType(data.layer_type || 'unknown');
                        updateMapFeatures(validFeatures, data.layer_type);
                        foundFeatures = true;
                    }
                    
                    const backendSearchLocation = data.search_location;
                    if (backendSearchLocation && 
                        backendSearchLocation.lat && 
                        backendSearchLocation.lon &&
                        backendSearchLocation.lat !== 0 && 
                        backendSearchLocation.lon !== 0 &&
                        backendSearchLocation.lat >= 50.5 && backendSearchLocation.lat <= 53.8 &&
                        backendSearchLocation.lon >= 3.0 && backendSearchLocation.lon <= 7.5) {
                        
                        console.log("📍 Setting search location from backend:", backendSearchLocation);
                        setSearchLocation(backendSearchLocation);
                    } else {
                        console.log("🔍 Trying to extract location from response");
                        const extractedLocation = extractLocationFromQuery(currentQuery, validFeatures);
                        if (extractedLocation) {
                            console.log("📍 Setting extracted location:", extractedLocation);
                            setSearchLocation(extractedLocation);
                        }
                    }
                    
                } else if (data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                }
                
                const assistantMessage = {
                    type: 'assistant',
                    content: responseContent,
                    timestamp: new Date()
                };
                
                setMessages(prev => [...prev, assistantMessage]);
                
            } catch (error) {
                console.error("❌ Query error:", error);
                
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

        // Update map features with intelligent styling
        const updateMapFeatures = (data, dataLayerType) => {
            if (!mapInstance.current) {
                console.error("❌ Map instance not available");
                return;
            }

            console.log(`🗺️ Updating map with ${data.length} features of type: ${dataLayerType}`);
            
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
                console.warn("⚠️ No features to display");
                return;
            }

            const vectorSource = new ol.source.Vector();
            let featuresAdded = 0;
            let boundsLats = [];
            let boundsLons = [];
            
            data.forEach((f, index) => {
                try {
                    if (!f.geometry || !f.lat || !f.lon || f.lat === 0 || f.lon === 0) {
                        console.warn(`⚠️ Skipping feature ${index + 1}: invalid data`);
                        return;
                    }
                    
                    if (f.lat < 50.5 || f.lat > 53.8 || f.lon < 3.0 || f.lon > 7.5) {
                        console.warn(`⚠️ Skipping feature ${index + 1}: outside Netherlands bounds: ${f.lat}, ${f.lon}`);
                        return;
                    }
                    
                    boundsLats.push(f.lat);
                    boundsLons.push(f.lon);
                    
                    let geom;
                    try {
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

            if (featuresAdded === 0) {
                console.error("❌ No features were successfully added to the map");
                return;
            }

            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => createIntelligentStyle(feature, dataLayerType)
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("✅ Vector layer added to map");
            
            if (boundsLats.length > 0 && boundsLons.length > 0) {
                const minLat = Math.min(...boundsLats);
                const maxLat = Math.max(...boundsLats);
                const minLon = Math.min(...boundsLons);
                const maxLon = Math.max(...boundsLons);
                
                const extent = ol.proj.transformExtent(
                    [minLon, minLat, maxLon, maxLat],
                    'EPSG:4326',
                    'EPSG:3857'
                );
                
                const padding = (dataLayerType === 'buildings' || dataLayerType === 'bag') ? [60, 60, 60, 300] : [60, 60, 60, 60];
                mapInstance.current.getView().fit(extent, { 
                    padding: padding,
                    maxZoom: 16,
                    duration: 1200
                });
                console.log("🎯 Map view fitted to features");
            }
        };

        // Clear map function
        const clearMap = () => {
            setFeatures([]);
            setLayerType(null);
            setSearchLocation(null);
            
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
                
                {/* Intelligent Location Pin Component */}
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
                        </div>
                    </div>
                </div>

                {/* Dynamic Legend */}
                {React.createElement(DynamicLegend, { layerType, features })}

                {/* Chat Interface */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-[600px] glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${
                                    isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-blue-400'
                                }`}></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">🧠 AI Assistant</h2>
                                    <p className="text-sm text-blue-100">
                                        {isLoading ? 'Processing...' : 'Ready for questions'}
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
                                        <p className="text-xs opacity-75 mt-1">Processing...</p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-4 border-t border-gray-200">
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    onClick={() => setQuery("Show buildings near Groningen")}
                                    className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded-full hover:bg-red-200 transition-colors"
                                >
                                    🏠 Buildings
                                </button>
                                <button
                                    onClick={() => setQuery("Agricultural land in Utrecht province")}
                                    className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                                >
                                    🌾 Land Use
                                </button>
                                <button
                                    onClick={() => setQuery("Large parcels in Amsterdam")}
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
                                    placeholder="Ask about Dutch spatial data..."
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
