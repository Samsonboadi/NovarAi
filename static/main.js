// static/main.js - FIXED Production Map-Aware PDOK Chat Assistant
console.log("Loading FIXED Production Map-Aware PDOK Chat Assistant with Enhanced Location Handling");

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
        console.log("Initializing FIXED Production Map component with Enhanced Location Handling");
        
        // State management
        const [query, setQuery] = useState('');
        const [messages, setMessages] = useState([
            {
                type: 'assistant',
                content: 'Hello! I\'m your FIXED map-aware AI Agent with enhanced location handling.\nI can help you explore buildings and plot them on the map with proper search location pins.\n\n🧭 Try asking:\n"Show me buildings near Leonard Springerlaan 37, Groningen."\n\n📐 Or get specific:\n"Show me buildings near Leonard Springerlaan 37, Groningen with area > 300m²."',
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

                // ENHANCED: Create location pin with better styling
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
                        <div id="pin-label" style="
                            margin-top: 8px;
                            background: rgba(239, 68, 68, 0.9);
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 11px;
                            font-weight: 600;
                            white-space: nowrap;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                            max-width: 200px;
                            text-overflow: ellipsis;
                            overflow: hidden;
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

        // ENHANCED: Show pin when searchLocation is set with better validation and debugging
        useEffect(() => {
            console.log("🔄 ENHANCED SEARCH LOCATION useEffect TRIGGERED");
            console.log("  - searchLocation:", searchLocation);
            console.log("  - locationPinRef.current:", !!locationPinRef.current);
            console.log("  - mapInstance.current:", !!mapInstance.current);
            
            if (searchLocation && locationPinRef.current && mapInstance.current) {
                console.log("📍 ENHANCED SEARCH LOCATION PROCESSING:");
                console.log("  - Name:", searchLocation.name);
                console.log("  - Latitude:", searchLocation.lat, typeof searchLocation.lat);
                console.log("  - Longitude:", searchLocation.lon, typeof searchLocation.lon);
                console.log("  - Source:", searchLocation.source);
                
                // ENHANCED: Validate coordinates with better error messages
                if (typeof searchLocation.lat !== 'number' || typeof searchLocation.lon !== 'number') {
                    console.error("❌ INVALID COORDINATE TYPES:");
                    console.error("  - lat:", searchLocation.lat, "type:", typeof searchLocation.lat);
                    console.error("  - lon:", searchLocation.lon, "type:", typeof searchLocation.lon);
                    return;
                }
                
                if (isNaN(searchLocation.lat) || isNaN(searchLocation.lon)) {
                    console.error("❌ NaN COORDINATES DETECTED:");
                    console.error("  - lat isNaN:", isNaN(searchLocation.lat));
                    console.error("  - lon isNaN:", isNaN(searchLocation.lon));
                    return;
                }
                
                // ENHANCED: Check if coordinates are within reasonable bounds for Netherlands
                if (searchLocation.lat < 50.5 || searchLocation.lat > 54.0 || 
                    searchLocation.lon < 3.0 || searchLocation.lon > 7.5) {
                    console.warn("⚠️ COORDINATES OUTSIDE EXPECTED NETHERLANDS BOUNDS:");
                    console.warn("  - Coordinates:", searchLocation.lat, searchLocation.lon);
                    console.warn("  - Expected bounds: lat 50.5-54.0, lon 3.0-7.5");
                    console.warn("  - Proceeding anyway...");
                }
                
                try {
                    console.log("🎯 POSITIONING SEARCH LOCATION PIN:");
                    
                    // Transform coordinates to map projection
                    const pinCoords = ol.proj.fromLonLat([searchLocation.lon, searchLocation.lat]);
                    console.log("🗺️ COORDINATE TRANSFORMATION:");
                    console.log("  - Input WGS84:", [searchLocation.lon, searchLocation.lat]);
                    console.log("  - Output map projection:", pinCoords);
                    
                    // Validate transformed coordinates
                    if (!Array.isArray(pinCoords) || pinCoords.length !== 2 || 
                        !isFinite(pinCoords[0]) || !isFinite(pinCoords[1])) {
                        console.error("❌ INVALID TRANSFORMED COORDINATES:", pinCoords);
                        return;
                    }
                    
                    // Set pin position
                    locationPinRef.current.setPosition(pinCoords);
                    console.log("✅ SEARCH LOCATION PIN POSITIONED SUCCESSFULLY");
                    
                    // Verify the pin position was set
                    const currentPosition = locationPinRef.current.getPosition();
                    console.log("🔍 VERIFICATION - Pin position after setting:", currentPosition);
                    
                    // ENHANCED: Update pin label with location name
                    const pinElement = locationPinRef.current.getElement();
                    if (pinElement) {
                        console.log("🏷️ UPDATING PIN LABEL");
                        const labelElement = pinElement.querySelector('#pin-label');
                        if (labelElement) {
                            // Truncate long names intelligently
                            let displayName = searchLocation.name;
                            if (displayName.length > 25) {
                                // Try to find a good break point
                                const words = displayName.split(' ');
                                if (words.length > 1) {
                                    displayName = words.slice(0, Math.ceil(words.length / 2)).join(' ') + '...';
                                } else {
                                    displayName = displayName.substring(0, 22) + '...';
                                }
                            }
                            
                            labelElement.textContent = displayName;
                            labelElement.title = searchLocation.name; // Full name on hover
                            console.log("✅ PIN LABEL UPDATED TO:", displayName);
                            console.log("📝 Full name available on hover:", searchLocation.name);
                        } else {
                            console.warn("⚠️ PIN LABEL ELEMENT NOT FOUND");
                        }
                    } else {
                        console.warn("⚠️ PIN ELEMENT NOT FOUND");
                    }
                    
                    // ENHANCED: Center map on search location with appropriate zoom
                    console.log("🗺️ CENTERING MAP ON SEARCH LOCATION");
                    const view = mapInstance.current.getView();
                    view.animate({
                        center: pinCoords,
                        zoom: Math.max(view.getZoom(), 15), // Ensure minimum zoom level
                        duration: 1000
                    });
                    console.log("✅ MAP CENTERED AND ANIMATED TO SEARCH LOCATION");
                    
                } catch (coordError) {
                    console.error("❌ ERROR IN ENHANCED COORDINATE PROCESSING:", coordError);
                }
                
            } else {
                console.log("📍 NO SEARCH LOCATION OR MISSING REFERENCES:");
                console.log("  - searchLocation exists:", !!searchLocation);
                console.log("  - locationPinRef.current exists:", !!locationPinRef.current);
                console.log("  - mapInstance.current exists:", !!mapInstance.current);
                
                // ENHANCED: Hide pin if no search location
                if (locationPinRef.current && mapInstance.current && !searchLocation) {
                    console.log("🚫 HIDING SEARCH LOCATION PIN");
                    locationPinRef.current.setPosition(undefined);
                }
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

        // ENHANCED: Chat query handler with better response processing
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
                console.log("🚀 ENHANCED: Sending query to FIXED backend:", currentQuery);
                
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
                console.log("📦 ENHANCED: FULL RESPONSE FROM FIXED BACKEND:", data);
                
                // ENHANCED: Process search location from backend response
                if (data && data.search_location) {
                    const searchLoc = data.search_location;
                    console.log("🎯 ENHANCED: PROCESSING SEARCH LOCATION FROM FIXED BACKEND:");
                    console.log("  - Name:", searchLoc.name);
                    console.log("  - Latitude:", searchLoc.lat);
                    console.log("  - Longitude:", searchLoc.lon);
                    console.log("  - Source:", searchLoc.source);
                    
                    // Validate coordinates before setting state
                    if (typeof searchLoc.lat === 'number' && typeof searchLoc.lon === 'number' &&
                        !isNaN(searchLoc.lat) && !isNaN(searchLoc.lon) &&
                        isFinite(searchLoc.lat) && isFinite(searchLoc.lon)) {
                        
                        console.log("✅ ENHANCED: COORDINATES ARE VALID - Setting search location state");
                        
                        setSearchLocation({
                            lat: searchLoc.lat,
                            lon: searchLoc.lon,
                            name: searchLoc.name,
                            source: searchLoc.source || 'backend'
                        });
                        
                        console.log("📍 ENHANCED: SEARCH LOCATION STATE SET SUCCESSFULLY");
                        
                    } else {
                        console.error("❌ ENHANCED: INVALID COORDINATES IN SEARCH LOCATION:");
                        console.error("  - lat:", searchLoc.lat, "type:", typeof searchLoc.lat, "isNaN:", isNaN(searchLoc.lat));
                        console.error("  - lon:", searchLoc.lon, "type:", typeof searchLoc.lon, "isNaN:", isNaN(searchLoc.lon));
                    }
                } else {
                    console.warn("⚠️ ENHANCED: NO SEARCH LOCATION IN BACKEND RESPONSE");
                    console.log("🔍 Response keys:", Object.keys(data || {}));
                }
                
                let responseContent = '';
                let foundBuildings = false;
                
                // ENHANCED: Process different response formats
                if (data && typeof data === 'object' && 'response' in data && 'geojson_data' in data) {
                    console.log("✅ ENHANCED: Detected combined response format");
                    
                    responseContent = data.response;
                    const geojsonData = data.geojson_data;
                    
                    if (Array.isArray(geojsonData) && geojsonData.length > 0) {
                        console.log("🗺️ ENHANCED: Processing building data for map display:", geojsonData.length);
                        
                        // Validate features before setting
                        const validFeatures = geojsonData.filter(feature => {
                            return feature && 
                                   typeof feature === 'object' && 
                                   typeof feature.lat === 'number' && 
                                   typeof feature.lon === 'number' &&
                                   !isNaN(feature.lat) && !isNaN(feature.lon) &&
                                   feature.lat !== 0 && feature.lon !== 0;
                        });
                        
                        console.log("✅ ENHANCED: Valid features after filtering:", validFeatures.length);
                        
                        if (validFeatures.length > 0) {
                            setFeatures(validFeatures);
                            updateMapFeatures(validFeatures);
                            foundBuildings = true;
                            
                            console.log("📊 ENHANCED: Features set for legend and statistics:", validFeatures.length);
                        } else {
                            console.warn("⚠️ ENHANCED: No valid features after validation");
                        }
                    } else {
                        console.log("📝 ENHANCED: Response has no geojson_data or empty array");
                    }
                }
                // Handle other response formats
                else if (data && data.response) {
                    responseContent = data.response;
                    console.log("📝 ENHANCED: Text-only response");
                }
                else if (data && data.error) {
                    responseContent = `I encountered an issue: ${data.error}`;
                    console.error("❌ ENHANCED: Backend returned error:", data.error);
                }
                else if (typeof data === 'string') {
                    responseContent = data;
                    console.log("📝 ENHANCED: String response");
                }
                else {
                    responseContent = JSON.stringify(data, null, 2);
                    console.log("📝 ENHANCED: JSON response (fallback)");
                }
                
                const assistantMessage = {
                    type: 'assistant',
                    content: responseContent,
                    timestamp: new Date()
                };
                
                setMessages(prev => [...prev, assistantMessage]);
                
                // ENHANCED: Provide feedback about what was processed
                if (foundBuildings) {
                    console.log("🎉 ENHANCED: Successfully processed geographic response with buildings");
                } else {
                    console.log("💬 ENHANCED: Processed text-only response");
                }
                
            } catch (error) {
                console.error("❌ ENHANCED QUERY ERROR:", error);
                
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

            console.log(`ENHANCED: Updating map with ${data.length} features`);
            
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
                console.log("ENHANCED: No data to display on map");
                return;
            }

            const vectorSource = new ol.source.Vector();
            let featuresAdded = 0;
            
            data.forEach((f, index) => {
                try {
                    if (!f.geometry || !f.lat || !f.lon || f.lat === 0 || f.lon === 0) {
                        console.warn(`ENHANCED: Skipping feature ${index + 1}: invalid data`);
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
                        console.error(`ENHANCED: Geometry processing error for feature ${index + 1}:`, geomError);
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
                    console.error(`ENHANCED: Error processing feature ${index + 1}:`, error);
                }
            });

            console.log(`ENHANCED: Total features added to map: ${featuresAdded}/${data.length}`);

            if (featuresAdded === 0) {
                console.error("ENHANCED: No features were successfully added to the map");
                return;
            }

            // ENHANCED STYLING with better visual hierarchy
            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: feature => {
                    const geomType = feature.getGeometry().getType();
                    const props = feature.get('properties') || {};
                    
                    if (geomType === 'Point') {
                        const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min || 0;
                        let pointColor = '#667eea';
                        let pointSize = 12;
                        
                        if (area > 1000) {
                            pointColor = '#dc2626';
                            pointSize = 16;
                        } else if (area > 500) {
                            pointColor = '#f97316';
                            pointSize = 14;
                        } else if (area > 200) {
                            pointColor = '#eab308';
                            pointSize = 13;
                        } else if (area > 0) {
                            pointColor = '#22c55e';
                            pointSize = 12;
                        }
                        
                        return new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: pointSize,
                                fill: new ol.style.Fill({ color: pointColor }),
                                stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 })
                            })
                        });
                        
                    } else if (geomType === 'Polygon') {
                        const year = props.bouwjaar;
                        const area = props.area_m2 || props.oppervlakte_max || props.oppervlakte_min || 0;
                        
                        let fillColor = 'rgba(102, 126, 234, 0.7)';
                        let strokeColor = '#667eea';
                        let strokeWidth = 2;
                        
                        // Priority: Color by area if available
                        if (area > 0) {
                            if (area > 1000) {
                                fillColor = 'rgba(220, 38, 38, 0.8)';
                                strokeColor = '#dc2626';
                                strokeWidth = 3;
                            } else if (area > 500) {
                                fillColor = 'rgba(249, 115, 22, 0.8)';
                                strokeColor = '#f97316';
                                strokeWidth = 3;
                            } else if (area > 200) {
                                fillColor = 'rgba(234, 179, 8, 0.8)';
                                strokeColor = '#eab308';
                                strokeWidth = 2;
                            } else {
                                fillColor = 'rgba(34, 197, 94, 0.8)';
                                strokeColor = '#22c55e';
                                strokeWidth = 2;
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
                                width: strokeWidth
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
            console.log("ENHANCED: Vector layer added to map");
            
            // ENHANCED: Fit to features with better padding and animation
            const extent = vectorSource.getExtent();
            
            if (extent && extent.every(coord => isFinite(coord))) {
                // If we have a search location, include it in the extent
                if (searchLocation) {
                    const searchCoords = ol.proj.fromLonLat([searchLocation.lon, searchLocation.lat]);
                    ol.extent.extend(extent, searchCoords);
                }
                
                mapInstance.current.getView().fit(extent, { 
                    padding: [80, 80, 80, 80], 
                    maxZoom: 17,
                    duration: 1500
                });
                console.log("ENHANCED: Map view fitted to features with animation");
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

                {/* ENHANCED Map Context Info */}
                <div className="absolute top-20 left-4 z-40 map-context-info">
                    <div className="floating-card p-3">
                        <div className="text-sm text-gray-700">
                            <p className="font-medium">FIXED Map View</p>
                            <p>Zoom: {mapZoom}</p>
                            {searchLocation && (
                                <div className="text-red-600 font-medium">
                                    <p>📍 {searchLocation.name}</p>
                                    <p className="text-xs">Source: {searchLocation.source}</p>
                                </div>
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
                                    <h2 className="text-lg font-semibold text-white">FIXED Agentic Mapper</h2>
                                    <p className="text-sm text-blue-100">Enhanced AI Assistant</p>
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
                                        <p className="text-xs opacity-75 mt-1">FIXED AI processing...</p>
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
                                    📍 Address + Pin + Plot
                                </button>
                                <button
                                    onClick={() => setQuery("Find buildings near Amsterdam Centraal larger than 500m²")}
                                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                                >
                                    🚉 Station Area
                                </button>
                                <button
                                    onClick={() => setQuery("Show historic buildings near Groningen train station built before 1950")}
                                    className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
                                >
                                    🏛️ Historic Search
                                </button>
                                <button
                                    onClick={() => setQuery("Show me buildings near Utrecht with area > 200m²")}
                                    className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded-full hover:bg-orange-200 transition-colors"
                                >
                                    ✅ FIXED Test
                                </button>
                            </div>
                            
                            <div className="flex space-x-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    className="flex-1 search-input rounded-xl px-4 py-2 text-sm focus:outline-none"
                                    placeholder="FIXED: Pins + JSON plotting working! 🎯📍🗺️"
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

                {/* ENHANCED Status Indicator */}
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
                            ✅ FIXED SYSTEM READY!
                        </div>
                        <div>📍 Pin: {searchLocation ? '✅' : '❌'}</div>
                        <div>🏠 Legend: ✅</div>
                        <div>📊 Stats: ✅</div>
                        <div>🗺️ JSON Plot: ✅</div>
                        <div>{features.length} buildings</div>
                        {searchLocation && (
                            <div style={{ fontSize: '10px', marginTop: '4px', color: '#dc2626' }}>
                                📍 {searchLocation.name}
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    console.log("Rendering FIXED Production Map-Aware React app with Enhanced Location Handling");
    
    if (root) {
        root.render(React.createElement(App));
    } else {
        ReactDOM.render(React.createElement(App), container);
    }
    
} catch (error) {
    console.error("Failed to initialize FIXED Production React app:", error);
}