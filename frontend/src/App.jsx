import { useState, useEffect, useMemo, useCallback, useDeferredValue, memo, useRef, useTransition } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Logo from './Logo'
import './conversation-styles.css'
import './intro.css'
import './draggable.css'
import './logo.css'
import {
  formatEmissionIntensity,
  formatAnnualEmissions,
  getLegendRanges,
  formatLegendRange,
  getMarkerColor as getMarkerColorWithUnit,
  getUnitLabel,
  saveUnitPreference,
  loadUnitPreference,
} from './unitConversions'

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const computeStats = (data) => {
  if (!data || data.length === 0) {
    return null
  }

  const values = data.map((point) => point.value)
  const sortedValues = [...values].sort((a, b) => a - b)
  const minValue = sortedValues[0]
  const maxValue = sortedValues[sortedValues.length - 1]
  const totalEmissions = values.reduce((sum, value) => sum + value, 0)
  const avgValue = totalEmissions / values.length
  const medianValue = sortedValues[Math.floor(sortedValues.length / 2)]

  return {
    minValue,
    maxValue,
    avgValue,
    totalEmissions,
    medianValue,
    dataPoints: values.length,
  }
}

const MAX_MARKERS_TO_RENDER = 800

// Component to handle zoom events smoothly
function ZoomHandler({ onZoomChange }) {
  useMapEvents({
    zoom: (e) => {
      // Update zoom level during animation for smooth marker scaling
      const newZoom = e.target.getZoom()
      onZoomChange(newZoom)
    },
  })
  return null
}

const EmissionsMap = memo(function EmissionsMap({ data, view, getMarkerColor, unitSystem }) {
  const [zoomLevel, setZoomLevel] = useState(11)
  const [mapCenter, setMapCenter] = useState([40.7128, -74.006])
  const [isMapReady, setIsMapReady] = useState(false)
  
  const points = useMemo(() => {
    if (!data || data.length === 0) return []
    if (data.length <= MAX_MARKERS_TO_RENDER) return data

    const step = Math.ceil(data.length / MAX_MARKERS_TO_RENDER)
    return data.filter((_, index) => index % step === 0)
  }, [data])

  if (!points.length) {
    return (
      <div className="map-loading">
        <div className="spinner"></div>
        <p>Loading emissions data...</p>
      </div>
    )
  }

  // Dynamic marker radius based on zoom level
  const getMarkerRadius = (zoom) => {
    const baseRadius = view === 'difference' ? 5 : 7
    // Scale radius based on zoom: more zoom = bigger markers
    // At zoom 11 (default): base radius
    // At zoom 15+: much larger markers
    // At zoom 8-: smaller markers
    const zoomFactor = Math.pow(1.5, zoom - 11) // Increased from 1.3 to 1.5 for more aggressive scaling
    return Math.max(3, Math.min(35, Math.round(baseRadius * zoomFactor))) // Increased max from 25 to 35
  }

  const markerRadius = getMarkerRadius(zoomLevel)

  return (
    <MapContainer
      center={mapCenter}
      zoom={zoomLevel}
      className="map"
      zoomAnimation={true}
      zoomAnimationThreshold={4}
    >
      <ZoomHandler onZoomChange={setZoomLevel} />

      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />

      {points.map((point, index) => (
        <CircleMarker
          key={`${point.lat}-${point.lon}-${index}`}
          center={[point.lat, point.lon]}
          radius={markerRadius}
          pathOptions={{
            fillColor: getMarkerColor(point.value, view),
            color: getMarkerColor(point.value, view),
            weight: 1.5,
            opacity: 0.8,
            fillOpacity: 0.6,
          }}
        >
          <Popup>
            <div className="popup-content">
              <h4 className="popup-title">
                {view === 'baseline'
                  ? 'Baseline Emissions'
                  : view === 'simulation'
                    ? 'Simulation Results'
                    : 'Impact Analysis'}
              </h4>
              <div className="popup-data">
                <p>
                  <strong>Coordinates:</strong> {point.lat.toFixed(4)}, {point.lon.toFixed(4)}
                </p>
                {view === 'difference' ? (
                  <>
                    <p>
                      <strong>Reduction:</strong> <span className="highlight">{point.value.toFixed(1)}%</span>
                    </p>
                    <p>
                      <strong>Before:</strong> {point.baselineValue ? formatEmissionIntensity(point.baselineValue, unitSystem) : '—'}
                    </p>
                    <p>
                      <strong>After:</strong> {point.simulationValue ? formatEmissionIntensity(point.simulationValue, unitSystem) : '—'}
                    </p>
                  </>
                ) : (
                  <p>
                    <strong>Emissions:</strong> <span className="highlight">{formatEmissionIntensity(point.value, unitSystem)}</span>
                  </p>
                )}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
})

EmissionsMap.displayName = 'EmissionsMap'

// Animated placeholder text component
const AnimatedPlaceholder = () => {
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const placeholders = [
    "Enter your climate intervention prompt...",
    "Convert 30% of taxis to electric vehicles...",
    "Install solar panels on 50% of buildings...",
    "Reduce industrial emissions by 25%...",
    "Implement green infrastructure...",
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return <span className="animated-placeholder">{placeholders[placeholderIndex]}</span>
}

// Intro Screen Component with Typing Animation
function IntroScreen({ onStart, isFadingOut }) {
  const [typedTitle, setTypedTitle] = useState('')
  const [typedSubtitle, setTypedSubtitle] = useState('')
  const [showButton, setShowButton] = useState(false)
  const [cursorVisible, setCursorVisible] = useState(true)
  
  const title = 'CO₂UNT'
  const subtitle = 'AI-Powered Climate Impact Simulator for NYC'
  
  useEffect(() => {
    // Type the title
    let titleIndex = 0
    const titleInterval = setInterval(() => {
      if (titleIndex < title.length) {
        setTypedTitle(title.slice(0, titleIndex + 1))
        titleIndex++
      } else {
        clearInterval(titleInterval)
        // Start typing subtitle after title is done
        setTimeout(() => {
          let subtitleIndex = 0
          const subtitleInterval = setInterval(() => {
            if (subtitleIndex < subtitle.length) {
              setTypedSubtitle(subtitle.slice(0, subtitleIndex + 1))
              subtitleIndex++
            } else {
              clearInterval(subtitleInterval)
              // Show button after subtitle is done
              setTimeout(() => {
                setShowButton(true)
                setCursorVisible(false)
              }, 300)
            }
          }, 40) // Speed of subtitle typing
        }, 500) // Pause before subtitle
      }
    }, 150) // Speed of title typing
    
    // Cursor blink effect
    const cursorInterval = setInterval(() => {
      setCursorVisible(prev => !prev)
    }, 530)
    
    return () => {
      clearInterval(titleInterval)
      clearInterval(cursorInterval)
    }
  }, [])
  
  return (
    <div className={`intro-screen ${isFadingOut ? 'fade-out' : ''}`}>
      <div className="intro-content">
        <h1 className="intro-title">
          {typedTitle}
          {typedTitle && typedTitle.length < title.length && cursorVisible && <span className="cursor">|</span>}
        </h1>
        
        <p className="intro-subtitle">
          {typedSubtitle}
          {typedSubtitle && typedSubtitle.length < subtitle.length && cursorVisible && <span className="cursor">|</span>}
        </p>
        
        {showButton && (
          <button className="intro-button" onClick={onStart}>
            <span>Let's Get Started</span>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        )}
        
        <div className="intro-features">
          {showButton && (
            <>
              <div className="feature-item fade-in-up" style={{ animationDelay: '0.1s' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                  <line x1="12" y1="22.08" x2="12" y2="12"/>
                </svg>
                <span>Real NYC Data</span>
              </div>
              
              <div className="feature-item fade-in-up" style={{ animationDelay: '0.2s' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                <span>Real-time Simulation</span>
              </div>
              
              <div className="feature-item fade-in-up" style={{ animationDelay: '0.3s' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                </svg>
                <span>AI-Powered Analysis</span>
              </div>
            </>
          )}
        </div>
      </div>
      
      <div className="intro-background">
        <div className="particle"></div>
        <div className="particle"></div>
        <div className="particle"></div>
        <div className="particle"></div>
        <div className="particle"></div>
      </div>
      
      {/* Skip button (subtle) */}
      <button className="skip-intro" onClick={onStart} title="Skip intro">
        Skip →
      </button>
    </div>
  )
}

function App() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [baseline, setBaseline] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [intervention, setIntervention] = useState(null)
  const [statistics, setStatistics] = useState(null)
  const [error, setError] = useState(null)
  const [currentView, setCurrentView] = useState('baseline')
  const [isBackendConnected, setIsBackendConnected] = useState(false)
  
  // Conversation history
  const [conversationHistory, setConversationHistory] = useState([])
  const [activeConversationIndex, setActiveConversationIndex] = useState(null)
  const [showHistory, setShowHistory] = useState(true)
  
  // Intro screen state
  const [showIntro, setShowIntro] = useState(true)
  const [introFadingOut, setIntroFadingOut] = useState(false)
  
  // Unit system preference
  const [unitSystem, setUnitSystem] = useState(() => loadUnitPreference())
  
  // Draggable sidebar state
  const [sidebarPosition, setSidebarPosition] = useState(() => {
    const saved = localStorage.getItem('co2unt_sidebar_position')
    return saved ? JSON.parse(saved) : { top: '80px', right: '20px' }
  })
  const [isDragging, setIsDragging] = useState(false)
  const sidebarRef = useRef(null)
  const dragOffset = useRef({ x: 0, y: 0 })

  useEffect(() => {
    // Check if user has seen intro before
    const hasSeenIntro = localStorage.getItem('co2unt_seen_intro')
    if (hasSeenIntro) {
      setShowIntro(false)
      loadBaseline()
    }
  }, [])

  const handleStartApp = () => {
    setIntroFadingOut(true)
    localStorage.setItem('co2unt_seen_intro', 'true')
    
    // Wait for fade out animation, then hide intro and load baseline
    setTimeout(() => {
      setShowIntro(false)
      loadBaseline()
    }, 800) // Match the CSS transition duration
  }
  
  // Handle unit system change
  const handleUnitChange = (event) => {
    const newUnit = event.target.value
    setUnitSystem(newUnit)
    saveUnitPreference(newUnit)
  }
  
  // Draggable sidebar handlers
  const handleMouseDown = (e) => {
    // Allow dragging from ANYWHERE in the sidebar
    e.preventDefault() // Prevent text selection while dragging
    setIsDragging(true)
    const rect = sidebarRef.current.getBoundingClientRect()
    dragOffset.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    }
  }
  
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDragging) return
      
      const newLeft = e.clientX - dragOffset.current.x
      const newTop = e.clientY - dragOffset.current.y
      
      // Keep within viewport bounds
      const maxX = window.innerWidth - (sidebarRef.current?.offsetWidth || 300)
      const maxY = window.innerHeight - (sidebarRef.current?.offsetHeight || 400)
      
      setSidebarPosition({
        left: `${Math.max(0, Math.min(newLeft, maxX))}px`,
        top: `${Math.max(0, Math.min(newTop, maxY))}px`,
        right: 'auto'
      })
    }
    
    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false)
        // Save position
        localStorage.setItem('co2unt_sidebar_position', JSON.stringify(sidebarPosition))
      }
    }
    
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, sidebarPosition])
  
  // Minimize feature removed - sidebar always visible
  
  const loadBaseline = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/baseline')
      if (!response.ok) throw new Error('Failed to fetch baseline data')
      
      const data = await response.json()
      setBaseline(data.grid)
      setIsBackendConnected(true)
    } catch (error) {
      console.error('Error loading baseline:', error)
      setError('Backend connection failed. Please ensure the server is running on port 8000.')
      setIsBackendConnected(false)
    }
  }

  const handleSimulate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post('http://localhost:8000/api/simulate', { prompt })
      const simulationData = res.data.grid
      const interventionData = res.data.intervention
      const statisticsData = res.data.statistics
      
      setSimulation(simulationData)
      setIntervention(interventionData)
      setStatistics(statisticsData)
      setCurrentView('simulation')
      
      // Debug: Log statistics to console
      console.log('[CO2UNT] Statistics received:', {
        is_increase: statisticsData?.is_increase,
        is_unrelated: statisticsData?.is_unrelated,
        direction: statisticsData?.direction,
        percentage_reduction: statisticsData?.percentage_reduction,
        annual_savings_tons_co2: statisticsData?.annual_savings_tons_co2
      })
      
      // Ensure statistics has required fields
      if (!statisticsData) {
        console.warn('[CO2UNT] No statistics data received from backend')
      }
      
      // Add to conversation history
      const newConversation = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        prompt: prompt,
        simulation: simulationData,
        intervention: interventionData,
        statistics: statisticsData,
        view: 'simulation'
      }
      
      setConversationHistory(prev => [...prev, newConversation])
      setActiveConversationIndex(conversationHistory.length)
      setPrompt('')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Simulation failed')
    }
    setLoading(false)
  }
  
  const loadConversation = (index) => {
    const conversation = conversationHistory[index]
    if (!conversation) return
    
    setSimulation(conversation.simulation)
    setIntervention(conversation.intervention)
    setStatistics(conversation.statistics)
    setCurrentView(conversation.view)
    setActiveConversationIndex(index)
  }
  
  const clearHistory = () => {
    if (window.confirm('Clear all conversation history?')) {
      setConversationHistory([])
      setActiveConversationIndex(null)
      setSimulation(null)
      setIntervention(null)
      setStatistics(null)
      setCurrentView('baseline')
    }
  }
  
  const deleteConversation = (index, event) => {
    event.stopPropagation() // Prevent triggering the card click
    
    const newHistory = conversationHistory.filter((_, i) => i !== index)
    setConversationHistory(newHistory)
    
    // If we deleted the active conversation, handle it
    if (activeConversationIndex === index) {
      // Switch to the previous conversation, or baseline if none left
      if (newHistory.length > 0) {
        const newActiveIndex = Math.max(0, index - 1)
        loadConversation(newActiveIndex)
        setActiveConversationIndex(newActiveIndex)
      } else {
        // No conversations left, go back to baseline
        setSimulation(null)
        setIntervention(null)
        setStatistics(null)
        setCurrentView('baseline')
        setActiveConversationIndex(null)
      }
    } else if (activeConversationIndex > index) {
      // Adjust active index if it's after the deleted one
      setActiveConversationIndex(activeConversationIndex - 1)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSimulate()
    }
  }

  const baselineMaxValue = useMemo(() => {
    if (!baseline || baseline.length === 0) return 0
    return baseline.reduce((max, point) => (point.value > max ? point.value : max), 0)
  }, [baseline])

  const differenceData = useMemo(() => {
    if (!baseline || !simulation) return null
    return baseline.map((baselinePoint, index) => {
      const simPoint = simulation?.[index] ?? baselinePoint
      const reduction = baselinePoint.value - simPoint.value
      const reductionPercent = baselinePoint.value ? (reduction / baselinePoint.value) * 100 : 0
      return {
        lat: baselinePoint.lat,
        lon: baselinePoint.lon,
        value: reductionPercent,
        baselineValue: baselinePoint.value,
        simulationValue: simPoint.value
      }
    })
  }, [baseline, simulation])

  const mapData = useMemo(() => {
    if (currentView === 'difference') return differenceData
    if (currentView === 'simulation') return simulation
    return baseline
  }, [currentView, baseline, simulation, differenceData])

  const deferredMapData = useDeferredValue(mapData)

  const stats = useMemo(() => computeStats(mapData), [mapData])

  const getMarkerColor = useCallback((value, view) => {
    if (view === 'difference') {
      if (value > 50) return '#10b981'
      if (value > 25) return '#84cc16'
      if (value > 10) return '#facc15'
      if (value > 0) return '#f97316'
      return '#ef4444'
    }

    // Use ACTUAL emission values (kg CO₂/km²/day) to match legend
    // NYC inventory-aligned ranges:
    // Peak Hotspots: >1,000,000 (airports, industrial)
    // Very High: 200,000-1,000,000 (dense Manhattan)
    // High: 80,000-200,000 (urban centers)
    // Medium: 30,000-80,000 (typical urban)
    // Low: <30,000 (parks, water, outer areas)
    
    if (value > 1000000) return 'rgba(127, 29, 29, 0.9)'  // Peak Hotspots
    if (value > 200000) return 'rgba(239, 68, 68, 0.8)'   // Very High
    if (value > 80000) return 'rgba(251, 146, 60, 0.7)'   // High
    if (value > 30000) return 'rgba(250, 204, 21, 0.7)'   // Medium
    return 'rgba(74, 222, 128, 0.6)'                      // Low
  }, [])

  const examplePrompts = [
    'Convert 30% of Manhattan taxis to electric vehicles',
    'Install solar panels on 50% of Brooklyn buildings',
    'Reduce industrial emissions by 25% in Queens',
    'Implement green roofs on 40% of Bronx buildings',
    'Add 25% sustainable aviation fuel at JFK Airport',
  ]

  // Show intro screen
  if (showIntro) {
    return <IntroScreen onStart={handleStartApp} isFadingOut={introFadingOut} />
  }
  
  return (
    <div className="app">
      {/* Conversation History Sidebar */}
      {showHistory && conversationHistory.length > 0 && (
        <aside 
          ref={sidebarRef}
          className={`conversation-sidebar glass slide-in-left draggable ${isDragging ? 'dragging' : ''}`}
          style={sidebarPosition}
          onMouseDown={handleMouseDown}
        >
          <div className="conversation-header" style={{ cursor: 'move' }}>
            <div className="conversation-header-title" style={{ flex: 1, cursor: 'move' }}>
              <span className="drag-handle" title="Drag to move" style={{ cursor: 'move', fontSize: '18px', marginRight: '8px' }}>⋮⋮</span>
              <h3 className="sidebar-title" style={{ cursor: 'move' }}>Conversation History</h3>
            </div>
            <div className="conversation-header-controls" style={{ display: 'flex', gap: '6px' }}>
              <button 
                className="header-control-btn" 
                onClick={(e) => { e.stopPropagation(); setShowHistory(false); }}
                title="Close sidebar"
                style={{ cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          </div>
          
          <div className="conversation-list">
            {conversationHistory.map((conv, index) => (
              <div
                key={conv.id}
                className={`conversation-item ${activeConversationIndex === index ? 'active' : ''}`}
                onClick={() => loadConversation(index)}
              >
                <button 
                  className="delete-conversation-btn"
                  onClick={(e) => deleteConversation(index, e)}
                  title="Delete this conversation"
                  aria-label="Delete conversation"
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                
                <div className="conversation-header">
                  <span className="conversation-number">#{index + 1}</span>
                  <span className="conversation-time">
                    {new Date(conv.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p className="conversation-prompt">{conv.prompt}</p>
                {conv.statistics && (
                  <div className="conversation-stats">
                    {conv.statistics?.is_unrelated ? (
                      <>
                        <span className="stat-badge neutral">0%</span>
                        <span className="stat-value neutral">No climate impact</span>
                      </>
                    ) : (
                      <>
                        <span className={`stat-badge ${conv.statistics?.is_increase ? 'warning' : 'success'}`}>
                          {conv.statistics?.is_increase ? '+' : '-'}{conv.statistics?.percentage_reduction || 0}%
                        </span>
                        <span className="stat-value">
                          {conv.statistics?.is_increase 
                            ? `+${formatAnnualEmissions(Math.abs(conv.statistics?.annual_savings_tons_co2 || 0), unitSystem, true)} added`
                            : `${formatAnnualEmissions(Math.abs(conv.statistics?.annual_savings_tons_co2 || 0), unitSystem, true)} saved`
                          }
                        </span>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </aside>
      )}
      
      {/* Toggle History Button (when hidden) */}
      {!showHistory && conversationHistory.length > 0 && (
        <button 
          className="toggle-history-btn glass"
          onClick={() => setShowHistory(true)}
          title="Show history"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="20" height="20">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{conversationHistory.length}</span>
        </button>
      )}
      
      {/* Premium Header with Logo */}
      <header className="header premium-header slide-in-down">
        <div className="header-content">
          <div className="header-left">
            <Logo size="small" />
            <div className="header-text">
              <h1 className="title">CO₂UNT</h1>
              <p className="subtitle">AI-Powered Climate Impact Simulator for NYC</p>
            </div>
          </div>
          
          <div className="header-right">
            <div className="unit-selector glass-morphism">
              <svg className="unit-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <select value={unitSystem} onChange={handleUnitChange} className="unit-select">
                <option value="metric">Metric</option>
                <option value="imperial">Imperial</option>
              </select>
            </div>
            
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className={`main-content fade-in ${showHistory && conversationHistory.length > 0 ? 'with-sidebar' : ''}`}>
        {/* Control Panel */}
        <div className="control-panel glass">
          <h2 className="panel-title">Simulation Controls</h2>
          
          <div className="input-container">
            <div className="input-wrapper">
              <textarea 
                className="prompt-input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder=" "
                disabled={loading}
                rows={3}
              />
              {!prompt && <AnimatedPlaceholder />}
            </div>
            
            <button 
              className="btn-primary"
              onClick={handleSimulate}
              disabled={loading || !prompt.trim()}
            >
              {loading ? (
                <>
                  <div className="btn-spinner"></div>
                  Running Simulation...
                </>
              ) : (
                <>
                  <svg className="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Run Simulation
                </>
              )}
            </button>
          </div>
          
          <div className="example-prompts">
            <h3 className="prompts-title">Example Interventions</h3>
            <div className="prompts-grid">
              {examplePrompts.map((example, index) => (
                <button
                  key={index}
                  className="prompt-chip"
                  onClick={() => setPrompt(example)}
                  disabled={loading}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Map Container */}
        <div className="map-section glass">
          <div className="map-header">
            <h2 className="section-title">Emissions Visualization</h2>
            <div className="view-controls">
              <button 
                className={`view-btn ${currentView === 'baseline' ? 'active' : ''}`}
                onClick={() => setCurrentView('baseline')}
                disabled={loading}
              >
                <span className="view-label">Baseline</span>
              </button>
              <button 
                className={`view-btn ${currentView === 'simulation' ? 'active' : ''}`}
                onClick={() => setCurrentView('simulation')}
                disabled={!simulation || loading}
              >
                <span className="view-label">Simulation</span>
              </button>
              <button 
                className={`view-btn ${currentView === 'difference' ? 'active' : ''}`}
                onClick={() => setCurrentView('difference')}
                disabled={!baseline || !simulation || loading}
              >
                <span className="view-label">Impact</span>
              </button>
            </div>
          </div>
          
          <div className="map-wrapper">
            <EmissionsMap data={deferredMapData} view={currentView} getMarkerColor={getMarkerColor} unitSystem={unitSystem} />
          </div>
          
          <div className="legend">
            <div className="legend-title">
              {currentView === 'difference' ? 'Reduction Level' : `Emission Intensity (${getUnitLabel('emission_intensity', unitSystem)})`}
            </div>
            <div className="legend-items">
              {currentView === 'difference' ? (
                <>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#10b981'}}></div>
                    <span>High Reduction (&gt;50%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#84cc16'}}></div>
                    <span>Medium-High (25-50%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#facc15'}}></div>
                    <span>Medium (10-25%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#f97316'}}></div>
                    <span>Low (0-10%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#ef4444'}}></div>
                    <span>No Reduction</span>
                  </div>
                </>
              ) : (
                <>
                  {getLegendRanges(unitSystem).map((range, idx) => (
                    <div key={idx} className="legend-item">
                      <div className="legend-color" style={{background: range.color}}></div>
                      <span>{range.label}</span>
                      <span className="legend-range">{formatLegendRange(range.min, range.max, unitSystem)}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      {(stats || statistics) && (
        <div className="stats-section fade-in">
          {statistics && (
            <div className="stat-card glass featured-stat">
              <h3 className="stat-card-title">Sector-Specific Emissions Impact</h3>
              <div className="stat-row-featured">
                <div className="stat-col">
                  <span className="stat-label-featured">Sector Baseline</span>
                  <span className="stat-value-featured">{formatAnnualEmissions(statistics?.baseline_tons_co2 || 0, unitSystem, false)} / year</span>
                </div>
                <div className="stat-divider">→</div>
                <div className="stat-col">
                  <span className="stat-label-featured">After Intervention</span>
                  <span className="stat-value-featured success">{formatAnnualEmissions(statistics?.reduced_tons_co2 || 0, unitSystem, false)} / year</span>
                </div>
              </div>
              <div className="stat-savings">
                {statistics?.is_unrelated ? (
                  <>
                    <span className="savings-label">Climate Impact</span>
                    <span className="savings-value neutral">No measurable effect</span>
                    <span className="savings-percent neutral">(0% change - unrelated query)</span>
                  </>
                ) : statistics ? (
                  <>
                    <span className="savings-label">
                      {statistics?.is_increase ? 'Annual Impact (Increased)' : 'Annual Savings'}
                    </span>
                    <span className={`savings-value ${statistics?.is_increase ? 'increase' : 'decrease'}`}>
                      {statistics?.is_increase ? '+' : ''}{formatAnnualEmissions(Math.abs(statistics?.annual_savings_tons_co2 || 0), unitSystem, false)} CO₂ / year
                    </span>
                    <span className={`savings-percent ${statistics?.is_increase ? 'increase' : 'decrease'}`}>
                      ({statistics?.is_increase ? '+' : ''}{statistics?.percentage_reduction || 0}% {statistics?.is_increase ? 'increase' : 'reduction'} in this sector)
                    </span>
                  </>
                ) : null}
              </div>
            </div>
          )}
          
          {stats && (
            <div className="stat-card glass">
              <h3 className="stat-card-title">Grid Statistics</h3>
              <p style={{ fontSize: '0.85rem', opacity: 0.8, marginBottom: '1rem', lineHeight: '1.4' }}>
                Coverage: ~2,249 km² grid (NYC + water bodies). Values are emission intensities (kg CO₂/km²/day). 
                Aligned with NYC GHG inventory benchmarks.
              </p>
              <div className="stat-grid">
                <div className="stat-item">
                  <span className="stat-label">Average per {unitSystem === 'imperial' ? 'mi²' : 'km²'}</span>
                  <span className="stat-value">{formatEmissionIntensity(stats?.avgValue || 0, unitSystem)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Median Value</span>
                  <span className="stat-value">{formatEmissionIntensity(stats?.medianValue || 0, unitSystem)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Peak Emissions</span>
                  <span className="stat-value">{formatEmissionIntensity(stats?.maxValue || 0, unitSystem)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Minimum Emissions</span>
                  <span className="stat-value">{formatEmissionIntensity(stats?.minValue || 0, unitSystem)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Data Points</span>
                  <span className="stat-value">{stats?.dataPoints?.toLocaleString() || '0'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Intervention Details */}
      {intervention && (
        <div className="intervention-details glass fade-in">
          <h3 className="details-title">Intervention Analysis</h3>
          <div className="details-grid">
            <div className="detail-item">
              <span className="detail-label">Target Sector</span>
              <span className="detail-value">{intervention.sector}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Location</span>
              <span className="detail-value">{intervention.borough || 'Citywide'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Reduction Target</span>
              <span className="detail-value">{intervention.reduction_percent || intervention.magnitude_percent}%</span>
            </div>
            <div className="detail-item full-width">
              <span className="detail-label">Description</span>
              <span className="detail-value">{intervention.description}</span>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-banner slide-down">
          <svg className="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
          <button className="error-close" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner-large"></div>
            <h3 className="loading-title">Running AI Simulation</h3>
            <p className="loading-text">Analyzing environmental impact...</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
