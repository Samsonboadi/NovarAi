console.log("Loading FIXED INTELLIGENT Production Map-Aware PDOK Chat Assistant");

try {
    const { useState, useEffect, useRef, useCallback } = React;
    
    const container = document.getElementById('root');
    const root = ReactDOM.createRoot ? ReactDOM.createRoot(container) : null;

    // FIXED: Better Location Pin Component
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
                
                // FIXED: Strict Netherlands bounds check
                if (lat < 50.5 || lat > 53.8 || lon < 3.0 || lon > 7.5) {
                    console.warn("⚠️ FIXED: Coordinates outside strict Netherlands bounds:", lat, lon);
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

    // FIXED: Enhanced Flexible Legend with Building Support
    const FlexibleLegend = ({ legendData }) => {
        if (!legendData || !legendData.categories || legendData.categories.length === 0) {
            return null;
        }
        
        const legendStyle = {
            position: 'fixed',
            bottom: '160px',
            left: '20px',
            zIndex: 998,
            maxWidth: '300px', // FIXED: Increased width for building legends
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '16px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(10px)'
        };
        
        return React.createElement('div', {
            style: legendStyle
        }, [
            // FIXED: Enhanced title with better icons
            React.createElement('div', {
                key: 'title',
                style: { 
                    fontSize: '13px', 
                    fontWeight: 'bold', 
                    marginBottom: '12px', 
                    color: '#1f2937',
                    display: 'flex',
                    alignItems: 'center'
                }
            }, legendData.title || '📊 Data Legend'),
            
            // FIXED: Categories with enhanced display for buildings
            ...legendData.categories.map((category, index) => 
                React.createElement('div', {
                    key: `category-${index}`,
                    style: { 
                        fontSize: '11px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        marginBottom: '8px',
                        justifyContent: 'space-between',
                        padding: '3px 0'
                    }
                }, [
                    React.createElement('div', {
                        key: 'left',
                        style: { display: 'flex', alignItems: 'center', flex: 1 }
                    }, [
                        React.createElement('div', {
                            key: 'color',
                            style: { 
                                width: '16px', 
                                height: '16px', 
                                backgroundColor: category.color, 
                                marginRight: '12px', 
                                borderRadius: '3px',
                                border: '1px solid rgba(0,0,0,0.2)',
                                flexShrink: 0
                            }
                        }),
                        React.createElement('span', { 
                            key: 'label', 
                            style: { 
                                color: '#4b5563', 
                                fontSize: '10px',
                                lineHeight: '1.3',
                                fontWeight: '500'
                            } 
                        }, category.label)
                    ]),
                    React.createElement('div', {
                        key: 'right',
                        style: { 
                            fontSize: '10px', 
                            color: '#6b7280',
                            fontWeight: '600',
                            minWidth: '35px',
                            textAlign: 'right',
                            backgroundColor: 'rgba(107, 114, 128, 0.1)',
                            padding: '2px 6px',
                            borderRadius: '8px'
                        }
                    }, [
                        category.count && React.createElement('span', { key: 'count' }, category.count),
                        category.range && React.createElement('span', { key: 'range' }, category.range)
                    ])
                ])
            ),
            
            // FIXED: Enhanced statistics section with building-specific details
            legendData.statistics && React.createElement('div', {
                key: 'stats',
                style: { 
                    fontSize: '10px', 
                    color: '#6b7280', 
                    marginTop: '14px', 
                    paddingTop: '12px', 
                    borderTop: '1px solid #e5e7eb',
                    lineHeight: '1.5'
                }
            }, [
                // FIXED: Building-specific statistics
                legendData.layer_type === 'buildings' && [
                    legendData.statistics.total_buildings && React.createElement('div', { 
                        key: 'total',
                        style: { marginBottom: '3px', fontWeight: '600' }
                    }, `📊 Total: ${legendData.statistics.total_buildings} buildings`),
                    
                    legendData.statistics.oldest_building && React.createElement('div', { 
                        key: 'oldest',
                        style: { marginBottom: '3px' }
                    }, `🏛️ Oldest: ${legendData.statistics.oldest_building}`),
                    
                    legendData.statistics.newest_building && React.createElement('div', { 
                        key: 'newest',
                        style: { marginBottom: '3px' }
                    }, `🏢 Newest: ${legendData.statistics.newest_building}`),
                    
                    legendData.statistics.average_year && React.createElement('div', { 
                        key: 'average',
                        style: { marginBottom: '3px' }
                    }, `📈 Average: ${legendData.statistics.average_year}`),
                    
                    legendData.statistics.buildings_with_year && React.createElement('div', { 
                        key: 'with_year',
                        style: { fontSize: '9px', fontStyle: 'italic', marginTop: '6px' }
                    }, `${legendData.statistics.buildings_with_year} buildings have known construction dates`)
                ],
                
                // General statistics for other data types
                legendData.layer_type !== 'buildings' && Object.entries(legendData.statistics).map(([key, value], index) => {
                    if (key === 'total_features') return null;
                    
                    let label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    
                    return React.createElement('div', {
                        key: `stat-${index}`,
                        style: { 
                            marginBottom: '3px',
                            display: 'flex',
                            justifyContent: 'space-between'
                        }
                    }, [
                        React.createElement('span', { key: 'label' }, label + ':'),
                        React.createElement('span', { key: 'value', style: { fontWeight: '600' } }, value)
                    ]);
                }).filter(Boolean)
            ])
        ]);
    };

    // FIXED: Smart Statistics Component with Building Intelligence
    const SmartStatistics = ({ features, legendData, layerType, searchLocation }) => {
        if (!features || !Array.isArray(features) || features.length === 0) {
            return null;
        }
        
        const statsStyle = {
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            zIndex: 998,
            maxWidth: '320px', // FIXED: Increased width
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '14px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            fontFamily: 'Inter, sans-serif',
            backdropFilter: 'blur(10px)'
        };
        
        // FIXED: Generate smart statistics based on layer type
        const layerTitle = layerType === 'buildings' || layerType === 'bag' ? 'Buildings' :
                          layerType === 'land_use' || layerType === 'bestandbodemgebruik' ? 'Land Use' :
                          layerType === 'parcels' || layerType === 'cadastral' ? 'Parcels' :
                          layerType === 'environmental' || layerType === 'natura2000' ? 'Protected Areas' :
                          'Features';
        
        return React.createElement('div', {
            style: statsStyle
        }, [
            React.createElement('div', {
                key: 'title',
                style: { fontSize: '13px', fontWeight: 'bold', marginBottom: '6px', color: '#1f2937' }
            }, `📊 ${layerTitle} Analysis`),
            
            React.createElement('div', {
                key: 'count',
                style: { fontSize: '11px', color: '#4b5563', marginBottom: '8px', fontWeight: '600' }
            }, `${features.length} ${layerTitle.toLowerCase()} found`),
            
            // Location info
            searchLocation && React.createElement('div', {
                key: 'location',
                style: { fontSize: '10px', color: '#6b7280', marginBottom: '8px' }
            }, `📍 Near: ${searchLocation.name}`),
            
            // FIXED: Building-specific statistics
            layerType === 'buildings' || layerType === 'bag' ? [
                // Show building age distribution
                React.createElement('div', {
                    key: 'building-stats',
                    style: { fontSize: '10px', color: '#6b7280', marginBottom: '6px' }
                }, [
                    React.createElement('div', { key: 'age-title', style: { fontWeight: '600', marginBottom: '4px' } }, '🏠 Age Distribution:'),
                    
                    // Calculate age stats from features
                    (() => {
                        const years = features
                            .map(f => f.properties?.bouwjaar)
                            .filter(year => year && !isNaN(parseInt(year)))
                            .map(year => parseInt(year));
                        
                        if (years.length === 0) {
                            return React.createElement('div', { key: 'no-years' }, 'No construction dates available');
                        }
                        
                        const categories = {
                            historic: years.filter(y => y < 1900).length,
                            prewar: years.filter(y => y >= 1900 && y < 1950).length,
                            postwar: years.filter(y => y >= 1950 && y < 1980).length,
                            late20th: years.filter(y => y >= 1980 && y < 2000).length,
                            modern: years.filter(y => y >= 2000).length
                        };
                        
                        return [
                            categories.historic > 0 && React.createElement('div', { key: 'hist' }, `Historic (pre-1900): ${categories.historic}`),
                            categories.prewar > 0 && React.createElement('div', { key: 'pre' }, `Pre-war (1900-49): ${categories.prewar}`),
                            categories.postwar > 0 && React.createElement('div', { key: 'post' }, `Post-war (1950-79): ${categories.postwar}`),
                            categories.late20th > 0 && React.createElement('div', { key: 'late' }, `Late 20th C (1980-99): ${categories.late20th}`),
                            categories.modern > 0 && React.createElement('div', { key: 'mod' }, `Modern (2000+): ${categories.modern}`)
                        ].filter(Boolean);
                    })()
                ])
            ] : [
                // Legend statistics for non-building data
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
                        React.createElement('span', { key: 'value', style: { fontWeight: '600' } }, value)
                    ]);
                }).filter(Boolean)
            ],
            
            // Layer type indicator
            React.createElement('div', {
                key: 'layer-type',
                style: { 
                    fontSize: '9px', 
                    color: '#9ca3af', 
                    marginTop: '10px', 
                    paddingTop: '8px', 
                    borderTop: '1px solid #e5e7eb',
                    fontStyle: 'italic'
                }
            }, `Source: PDOK ${layerType} service`)
        ]);
    };

    const App = () => {
        console.log("Initializing FIXED INTELLIGENT Map component");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your FIXED intelligent PDOK assistant.\n\n🧠 I can analyze your queries and provide spatial data efficiently.\n\n📍 Location pins are automatically plotted when you mention places!\n🏠 Building searches now include age-based color coding and legends!\n\nTry asking:\n"Show buildings near Groningen"\n"Agricultural land in Utrecht province"\n"Large parcels in Amsterdam"',
                timestamp: new Date()
            }
        ]);
        const [features, setFeatures] = useState([]);
        const [isChatOpen, setIsChatOpen] = useState(false);
        const [isLoading, setIsLoading] = useState(false);
        const [mapView, setMapView] = useState('satellite');
        const [mapCenter, setMapCenter] = useState([5.2913, 52.1326]);
        const [mapZoom, setMapZoom] = useState(8);
        
        // FIXED: Enhanced state for intelligent features
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

        // FIXED: Debug state changes
        useEffect(() => {
            console.log("🔄 FIXED state update:", {
                features: features.length,
                searchLocation: searchLocation?.name,
                legendData: !!legendData,
                layerType,
                processingStatus
            });
        }, [features, searchLocation, legendData, layerType, processingStatus]);

        // Initialize OpenLayers map
        useEffect(() => {
            console.log("🗺️ Setting up FIXED intelligent OpenLayers map");
            
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

                // FIXED: Initialize location pin overlay
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

                // FIXED: Enhanced click handler with building-specific popups
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
                        
                        // FIXED: Enhanced popup content for buildings
                        let popupContent = `
                            <div class="space-y-2">
                                <h3 class="text-sm font-semibold text-gray-800">${name}</h3>
                                <div class="text-xs text-gray-600">
                                    <p><span class="font-medium">Coordinates:</span> ${lonLat[1].toFixed(6)}, ${lonLat[0].toFixed(6)}</p>
                                    ${description ? `<p class="mt-1">${description}</p>` : ''}
                        `;
                        
                        // FIXED: Add building-specific details
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

                console.log("✅ FIXED intelligent map setup complete");

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

        // FIXED: Intelligent building styling function
        const createIntelligentStyle = (feature, layerType, legendData) => {
            const geomType = feature.getGeometry().getType();
            const props = feature.get('properties') || {};
            
            let fillColor = 'rgba(102, 126, 234, 0.7)';
            let strokeColor = '#667eea';
            let strokeWidth = 2;
            
            // FIXED: Building-specific styling with age-based colors matching legend
            if (layerType === 'buildings' || layerType === 'bag') {
                const year = props.bouwjaar;
                if (year && !isNaN(parseInt(year))) {
                    const buildingYear = parseInt(year);
                    
                    if (buildingYear < 1900) {
                        // Historic buildings - Dark Red
                        fillColor = 'rgba(139, 0, 0, 0.8)';
                        strokeColor = '#8B0000';
                    } else if (buildingYear < 1950) {
                        // Pre-war buildings - Orange Red
                        fillColor = 'rgba(255, 69, 0, 0.8)';
                        strokeColor = '#FF4500';
                    } else if (buildingYear < 1980) {
                        // Post-war buildings - Green
                        fillColor = 'rgba(50, 205, 50, 0.8)';
                        strokeColor = '#32CD32';
                    } else if (buildingYear < 2000) {
                                 // Late 20th Century - Blue
                        fillColor = 'rgba(30, 144, 255, 0.8)';
                        strokeColor = '#1E90FF';
                    } else {
                        // Modern buildings - Pink
                        fillColor = 'rgba(255, 20, 147, 0.8)';
                        strokeColor = '#FF1493';
                    }
                } else {
                    // Unknown age - Gray
                    fillColor = 'rgba(128, 128, 128, 0.7)';
                    strokeColor = '#808080';
                }
            } else if (layerType === 'land_use' || layerType === 'bestandbodemgebruik') {
                // Land use styling
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
                // Parcel styling
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

        // FIXED: Intelligent query handling with building-specific messaging
        const handleQuery = async () => {
            if (!query.trim()) return;
            
            const userMessage = {
                type: 'user',
                content: query,
                timestamp: new Date()
            };
            
            setMessages(prev => [...prev, userMessage]);
            setIsLoading(true);
            
            // FIXED: Detect building queries for better status messaging
            const isBuildingQuery = query.toLowerCase().includes('building') || 
                                   query.toLowerCase().includes('house') ||
                                   query.toLowerCase().includes('construction') ||
                                   query.toLowerCase().includes('pand');
            
            setProcessingStatus(isBuildingQuery ? 'analyzing_buildings' : 'analyzing');
            const currentQuery = query;
            setQuery('');

            try {
                console.log("🧠 FIXED: Sending intelligent query:", currentQuery);
                
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: currentQuery
                    })
                });
                
                const data = await res.json();
                console.log("🎯 FIXED: Received intelligent response:", data);
                
                setProcessingStatus('processing');
                
                let responseContent = '';
                let foundFeatures = false;
                
                if (data && typeof data === 'object') {
                    responseContent = data.response || data.message || 'Analysis completed.';
                    
                    // FIXED: Extract and validate features with building detection
                    const geojsonData = data.geojson_data || [];
                    console.log(`📦 FIXED: Processing ${geojsonData.length} features`);
                    
                    // FIXED: Strict validation for Netherlands bounds
                    const validFeatures = geojsonData.filter(feature => {
                        return feature && 
                               typeof feature === 'object' && 
                               'lat' in feature && 
                               'lon' in feature && 
                               feature.lat !== 0 && 
                               feature.lon !== 0 &&
                               feature.lat >= 50.5 && feature.lat <= 53.8 &&  // FIXED: Strict bounds
                               feature.lon >= 3.0 && feature.lon <= 7.5;
                    });
                    
                    console.log(`✅ FIXED: ${validFeatures.length} valid features after strict validation`);
                    
                    if (validFeatures.length > 0) {
                        setFeatures(validFeatures);
                        setLayerType(data.layer_type || 'unknown');
                        
                        // FIXED: Enhanced legend data handling
                        const receivedLegendData = data.legend_data;
                        if (receivedLegendData) {
                            console.log("🏷️ FIXED: Received legend data:", receivedLegendData);
                            setLegendData(receivedLegendData);
                        } else if (isBuildingQuery) {
                            // FIXED: Generate fallback building legend if none provided
                            console.log("🏷️ FIXED: Generating fallback building legend");
                            const fallbackLegend = generateFallbackBuildingLegend(validFeatures);
                            setLegendData(fallbackLegend);
                        } else {
                            setLegendData(null);
                        }
                        
                        setProcessingStatus('success');
                        foundFeatures = true;
                        
                        // FIXED: Update map with features and correct legend data
                        updateMapFeatures(validFeatures, data.layer_type, legendData);
                    }
                    
                    // FIXED: Always handle search location with better extraction
                    const backendSearchLocation = data.search_location;
                    if (backendSearchLocation && 
                        backendSearchLocation.lat && 
                        backendSearchLocation.lon &&
                        backendSearchLocation.lat !== 0 && 
                        backendSearchLocation.lon !== 0 &&
                        backendSearchLocation.lat >= 50.5 && backendSearchLocation.lat <= 53.8 &&
                        backendSearchLocation.lon >= 3.0 && backendSearchLocation.lon <= 7.5) {
                        
                        console.log("📍 FIXED: Setting search location from backend:", backendSearchLocation);
                        setSearchLocation(backendSearchLocation);
                    } else {
                        // FIXED: Try to extract location from query text or features
                        console.log("🔍 FIXED: Trying to extract location from response");
                        const extractedLocation = extractLocationFromQuery(currentQuery, validFeatures);
                        if (extractedLocation) {
                            console.log("📍 FIXED: Setting extracted location:", extractedLocation);
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
                console.error("❌ FIXED query error:", error);
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

        // FIXED: Enhanced building legend creation with better logging
        const generateFallbackBuildingLegend = (features) => {
            try {
                console.log("🏷️ FIXED: Generating fallback building legend for", features.length, "features");
                
                const legend = {
                    "layer_type": "buildings",
                    "title": "🏠 Buildings by Age",
                    "categories": [],
                    "statistics": {}
                };
                
                // Analyze building years from features
                const buildingYears = [];
                let featuresWithYears = 0;
                
                for (const feature of features) {
                    const year = feature.properties?.bouwjaar;
                    if (year && !isNaN(parseInt(year))) {
                        buildingYears.push(parseInt(year));
                        featuresWithYears++;
                    }
                }
                
                console.log(`📊 FIXED: Found ${featuresWithYears} buildings with construction years out of ${features.length} total`);
                
                if (buildingYears.length === 0) {
                    // Return a simple legend for buildings without years
                    return {
                        "layer_type": "buildings",
                        "title": "🏠 Buildings",
                        "categories": [{
                            "label": "Buildings (age unknown)",
                            "color": "#32CD32",  // Use green as default
                            "count": features.length
                        }],
                        "statistics": {
                            "total_buildings": features.length,
                            "buildings_with_year": 0
                        }
                    };
                }
                
                // Create age categories with colors EXACTLY matching the map styling
                const ageCategories = [
                    {"label": "Historic (< 1900)", "color": "#8B0000", "min_year": 0, "max_year": 1899, "count": 0},
                    {"label": "Pre-war (1900-1949)", "color": "#FF4500", "min_year": 1900, "max_year": 1949, "count": 0},
                    {"label": "Post-war (1950-1979)", "color": "#32CD32", "min_year": 1950, "max_year": 1979, "count": 0},
                    {"label": "Late 20th C (1980-1999)", "color": "#1E90FF", "min_year": 1980, "max_year": 1999, "count": 0},
                    {"label": "Modern (2000+)", "color": "#FF1493", "min_year": 2000, "max_year": 9999, "count": 0}
                ];
                
                // Count buildings in each category
                for (const year of buildingYears) {
                    for (const category of ageCategories) {
                        if (year >= category.min_year && year <= category.max_year) {
                            category.count++;
                            break;
                        }
                    }
                }
                
                // Only include categories with buildings
                legend.categories = ageCategories.filter(cat => cat.count > 0);
                
                console.log(`🏷️ FIXED: Created ${legend.categories.length} legend categories:`, 
                    legend.categories.map(c => `${c.label}: ${c.count} (${c.color})`));
                
                // Add comprehensive statistics
                legend.statistics = {
                    "total_buildings": features.length,
                    "buildings_with_year": buildingYears.length,
                    "oldest_building": Math.min(...buildingYears),
                    "newest_building": Math.max(...buildingYears),
                    "average_year": Math.round(buildingYears.reduce((a, b) => a + b, 0) / buildingYears.length)
                };
                
                return legend;
                
            } catch (error) {
                console.error("❌ Error generating fallback building legend:", error);
                return {
                    "layer_type": "buildings",
                    "title": "🏠 Buildings",
                    "categories": [{
                        "label": "Buildings",
                        "color": "#32CD32",
                        "count": features.length
                    }]
                };
            }
        };

        // FIXED: Extract location from query text as fallback
        const extractLocationFromQuery = (queryText, features) => {
            const locationPatterns = [
                /(?:in|near|around|at)\s+([A-Za-z][A-Za-z\s]+?)(?:\s|$|,|\.|province)/i,
                /([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:province|area|city)/i,
                /([A-Za-z]+)(?:\s|$)/i  // FIXED: Fallback pattern
            ];
            
            for (const pattern of locationPatterns) {
                const match = queryText.match(pattern);
                if (match) {
                    const locationName = match[1].trim();
                    
                    // FIXED: If we have features, use their centroid with validation
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

        // FIXED: Update map features with intelligent styling and legend support
        const updateMapFeatures = (data, dataLayerType, legendData) => {
            if (!mapInstance.current) {
                console.error("❌ Map instance not available");
                return;
            }

            console.log(`🗺️ FIXED: Updating map with ${data.length} features of type: ${dataLayerType}`);
            
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
            let boundsLats = [];
            let boundsLons = [];
            
            data.forEach((f, index) => {
                try {
                    if (!f.geometry || !f.lat || !f.lon || f.lat === 0 || f.lon === 0) {
                        console.warn(`⚠️ Skipping feature ${index + 1}: invalid data`);
                        return;
                    }
                    
                    // FIXED: Strict Netherlands bounds validation
                    if (f.lat < 50.5 || f.lat > 53.8 || f.lon < 3.0 || f.lon > 7.5) {
                        console.warn(`⚠️ FIXED: Skipping feature ${index + 1}: outside strict Netherlands bounds: ${f.lat}, ${f.lon}`);
                        return;
                    }
                    
                    boundsLats.push(f.lat);
                    boundsLons.push(f.lon);
                    
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

            console.log(`✅ FIXED: Added ${featuresAdded}/${data.length} valid features to map`);

            if (featuresAdded === 0) {
                console.error("❌ No features were successfully added to the map");
                return;
            }

            // FIXED: Create layer with intelligent styling
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => createIntelligentStyle(feature, dataLayerType, legendData)
            });

            mapInstance.current.addLayer(vectorLayer);
            console.log("✅ Vector layer added to map");
            
            // FIXED: Better map fitting with padding for legend
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
                
                mapInstance.current.getView().fit(extent, { 
                    padding: [60, 350, 220, 60], // FIXED: Extra padding for legend on left
                    maxZoom: 16,
                    duration: 1200
                });
                console.log("🎯 FIXED: Map view fitted to features with legend padding");
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
                
                {/* FIXED: Intelligent Location Pin Component */}
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
                            <p className="font-medium">🧠 FIXED Intelligent Map</p>
                            <p>Zoom: {mapZoom}</p>
                            {searchLocation && (
                                <p className="text-red-600 font-medium">📍 {searchLocation.name}</p>
                            )}
                            {features.length > 0 && (
                                <p className="text-blue-600 font-medium">
                                    {features.length} {layerType || 'Features'}
                                </p>
                            )}
                            {/* FIXED: Enhanced legend status display */}
                            {legendData && (
                                <p className="text-purple-600 font-medium text-xs">
                                    🏷️ Legend: {legendData.categories?.length || 0} categories
                                </p>
                            )}
                            {!legendData && features.length > 0 && (layerType === 'buildings' || layerType === 'bag') && (
                                <p className="text-orange-600 font-medium text-xs">
                                    ⚠️ Legend: Missing
                                </p>
                            )}
                            <p className={`text-xs ${
                                processingStatus === 'success' ? 'text-green-600' :
                                processingStatus === 'error' ? 'text-red-600' :
                                processingStatus === 'analyzing' || processingStatus === 'analyzing_buildings' ? 'text-yellow-600' :
                                'text-gray-500'
                            }`}>
                                Status: {processingStatus.replace('_', ' ')}
                            </p>
                        </div>
                    </div>
                </div>

                {/* FIXED: Chat Interface with building-aware examples */}
                {isChatOpen ? (
                    <div className="fixed bottom-6 right-6 w-96 h-[600px] glass-effect rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-up">
                        {/* Chat Header */}
                        <div className="chat-gradient p-4 rounded-t-2xl flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${
                                    processingStatus === 'analyzing' || processingStatus === 'analyzing_buildings' ? 'bg-yellow-400 animate-pulse' :
                                    processingStatus === 'success' ? 'bg-green-400' :
                                    processingStatus === 'error' ? 'bg-red-400' :
                                    'bg-blue-400'
                                }`}></div>
                                <div>
                                    <h2 className="text-lg font-semibold text-white">🧠 FIXED AI Assistant</h2>
                                    <p className="text-sm text-blue-100">
                                        {processingStatus === 'analyzing' ? 'Analyzing query...' :
                                         processingStatus === 'analyzing_buildings' ? 'Analyzing buildings...' :
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
                                        <p className="text-xs opacity-75 mt-1">
                                            {processingStatus === 'analyzing_buildings' ? '🏠 Analyzing buildings...' : '🧠 Processing intelligently...'}
                                        </p>
                                    </div>
                                </div>
                            )}
                            
                            <div ref={messagesEndRef} />
                        </div>

                        {/* FIXED: Input Area with building-aware examples */}
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
                                    placeholder="Ask about Dutch spatial data... 🏠📍"
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

                {/* FIXED: Smart Statistics Component */}
                {React.createElement(SmartStatistics, { 
                    features: features,
                    legendData: legendData,
                    layerType: layerType,
                    searchLocation: searchLocation
                })}

                {/* FIXED: Enhanced Legend Component */}
                {React.createElement(FlexibleLegend, { 
                    legendData: legendData 
                })}

                {/* FIXED: Intelligent Status Indicator */}
                {(features.length > 0 || searchLocation || processingStatus !== 'ready') && (
                    <div style={{
                        position: 'fixed',
                        top: '50%',
                        right: '20px',
                        transform: 'translateY(-50%)',
                        zIndex: 999,
                        backgroundColor: processingStatus === 'success' ? 'rgba(34, 197, 94, 0.1)' : 
                                        processingStatus === 'error' ? 'rgba(239, 68, 68, 0.1)' : 
                                        processingStatus === 'analyzing' || processingStatus === 'analyzing_buildings' ? 'rgba(245, 158, 11, 0.1)' :
                                        'rgba(59, 130, 246, 0.1)',
                        border: `2px solid ${processingStatus === 'success' ? '#22c55e' : 
                                            processingStatus === 'error' ? '#ef4444' : 
                                            processingStatus === 'analyzing' || processingStatus === 'analyzing_buildings' ? '#f59e0b' :
                                            '#3b82f6'}`,
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '11px',
                        color: processingStatus === 'success' ? '#15803d' : 
                               processingStatus === 'error' ? '#dc2626' : 
                               processingStatus === 'analyzing' || processingStatus === 'analyzing_buildings' ? '#d97706' :
                               '#1d4ed8',
                        minWidth: '140px'
                    }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                            {processingStatus === 'success' ? '✅ FIXED SUCCESS!' : 
                             processingStatus === 'error' ? '❌ ERROR' : 
                             processingStatus === 'analyzing' ? '🧠 ANALYZING...' :
                             processingStatus === 'analyzing_buildings' ? '🏠 BUILDING ANALYSIS...' :
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

                {/* FIXED: Smart Help Overlay */}
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
                        maxWidth: '450px',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px', color: '#1f2937' }}>
                            🧠 FIXED Intelligent PDOK Assistant
                        </div>
                        <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.4', marginBottom: '12px' }}>
                            I analyze your queries intelligently and automatically plot locations with legends!
                        </div>
                        <div style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.3' }}>
                            <strong>🎯 FIXED Smart Features:</strong><br/>
                            📍 <strong>Auto Location Pins:</strong> Mention any Dutch place<br/>
                            🏠 <strong>Building Analysis:</strong> Age-based color coding with legends<br/>
                            🧠 <strong>Intelligent Analysis:</strong> I understand what you need<br/>
                            ⚡ <strong>Smart Radius:</strong> 2-3km for buildings, larger for regions<br/>
                            🏷️ <strong>Dynamic Legends:</strong> Generated for each data type
                        </div>
                        <div style={{ fontSize: '11px', color: '#4b5563', marginTop: '12px', lineHeight: '1.3' }}>
                            <strong>Try saying:</strong><br/>
                            "Show buildings near Groningen" (FIXED with 2km radius)<br/>
                            "Agricultural land in Utrecht province"<br/>
                            "Large parcels in Amsterdam"
                        </div>
                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '12px', fontStyle: 'italic' }}>
                            🚀 Powered by FIXED intelligent query analysis with building legends
                        </div>
                    </div>
                )}

                {/* FIXED: Processing Animation Overlay */}
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
                                🧠 FIXED Intelligent Processing
                            </div>
                            <div style={{
                                fontSize: '12px',
                                color: '#6b7280',
                                marginBottom: '12px'
                            }}>
                                {processingStatus === 'analyzing' ? 'Analyzing your query...' :
                                 processingStatus === 'analyzing_buildings' ? 'Analyzing buildings with age detection...' :
                                 processingStatus === 'processing' ? 'Fetching spatial data with smart radius...' :
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

    console.log("🚀 Rendering FIXED INTELLIGENT Production Map-Aware React app");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("❌ Failed to initialize FIXED INTELLIGENT React app:", error);
}