import { useState, useEffect, useMemo, useCallback, useDeferredValue, memo, useRef, useTransition } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Logo from './Logo'
import './conversation-styles.css'
import './intro.css'
import './draggable.css'
import {
  formatEmissionIntensity,
  formatAnnualEmissions,
  formatEmissionsWithPeriod,
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

  const values = data.map((point) => (point.value))
  const totalEmissions = values.reduce((sum, value) => sum + value, 0)
  const avgValue = totalEmissions / values.length

  return {
    avgValue,
    totalEmissions,
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
    const baseRadius = 7 // Same base radius for all views
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
                      <strong>Emissions:</strong> <span className="highlight">{point.simulationValue ? formatEmissionIntensity(point.simulationValue, unitSystem) : '—'}</span>
                    </p>
                    <p>
                      <strong>Reduction:</strong> {point.value.toFixed(1)}%
                    </p>
                    <p style={{ fontSize: '0.85em', opacity: 0.8 }}>
                      <strong>Before:</strong> {point.baselineValue ? formatEmissionIntensity(point.baselineValue, unitSystem) : '—'}
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
  const [isVisible, setIsVisible] = useState(true)
  const placeholders = [
    "Enter your climate intervention prompt...",
    "Convert 30% of taxis to electric vehicles...",
    "Install solar panels on 50% of buildings...",
    "Reduce industrial emissions by 25%...",
    "Implement green infrastructure...",
  ]

  useEffect(() => {
    const cyclePlaceholder = () => {
      setIsVisible(false) // Start fade out

      setTimeout(() => {
        setPlaceholderIndex((prev) => (prev + 1) % placeholders.length) // Change text

        // Use requestAnimationFrame to ensure DOM has updated before fading in
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setIsVisible(true) // Start fade in
          })
        })
      }, 500) // Wait for fade out to complete
    }

    const interval = setInterval(cyclePlaceholder, 3500) // Increased to 3.5s to account for full transition
    return () => clearInterval(interval)
  }, [placeholders.length])

  return (
    <span
      className="animated-placeholder"
      style={{
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 0.5s ease-in-out'
      }}
    >
      {placeholders[placeholderIndex]}
    </span>
  )
}

// Intro Screen Component with Typing Animation
function IntroScreen({ onStart, isFadingOut }) {
  const [typedTitle, setTypedTitle] = useState('')
  const [typedSubtitle, setTypedSubtitle] = useState('')
  const [showButton, setShowButton] = useState(false)
  const [cursorVisible, setCursorVisible] = useState(true)
  
  const title = 'CarbonIQ'
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
        <div className="intro-logo" style={{ marginBottom: '2rem' }}>
          <Logo size="xlarge" />
        </div>
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
  const [baselineMetadata, setBaselineMetadata] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [simulationStats, setSimulationStats] = useState(null) // Store simulation stats separately
  const [intervention, setIntervention] = useState(null)
  const [statistics, setStatistics] = useState(null)
  const [error, setError] = useState(null)
  const [currentView, setCurrentView] = useState('baseline')
  const [isBackendConnected, setIsBackendConnected] = useState(false)
  const [baselineAverage, setBaselineAverage] = useState(null)

  // Conversation history
  const [conversationHistory, setConversationHistory] = useState([])
  const [activeConversationIndex, setActiveConversationIndex] = useState(null)
  const [showHistory, setShowHistory] = useState(true)
  const [isHistoryExpanded, setIsHistoryExpanded] = useState(false)
  
  // Intro screen state
  const [showIntro, setShowIntro] = useState(true)
  const [introFadingOut, setIntroFadingOut] = useState(false)
  
  // Unit system preference
  const [unitSystem, setUnitSystem] = useState(() => loadUnitPreference())
  
  // Time period preferences (daily/annual) - independent for each section
  const [gridStatsTimePeriod, setGridStatsTimePeriod] = useState(() => {
    const saved = localStorage.getItem('carboniq_grid_time_period')
    return saved || 'annual'
  })
  
  const [intervSummaryTimePeriod, setIntervSummaryTimePeriod] = useState(() => {
    const saved = localStorage.getItem('carboniq_interv_time_period')
    return saved || 'annual'
  })
  
  // Draggable sidebar state
  const [sidebarPosition, setSidebarPosition] = useState(() => {
    const saved = localStorage.getItem('carboniq_sidebar_position_expanded')
    if (saved) {
      const parsed = JSON.parse(saved)
      // Clean up old centered position format (has transform property)
      if (parsed.transform) {
        localStorage.removeItem('carboniq_sidebar_position_expanded')
        return { bottom: '2rem', left: '2rem' }
      }
      return parsed
    }
    // Default to bottom-left corner on first open
    return { bottom: '2rem', left: '2rem' }
  })
  const [isDragging, setIsDragging] = useState(false)
  const sidebarRef = useRef(null)
  const dragOffset = useRef({ x: 0, y: 0 })

  useEffect(() => {
    // Check if user has seen intro before
    const hasSeenIntro = localStorage.getItem('carboniq_seen_intro')
    if (hasSeenIntro) {
      setShowIntro(false)
      loadBaseline()
    }
  }, [])

  const handleStartApp = () => {
    setIntroFadingOut(true)
    localStorage.setItem('carboniq_seen_intro', 'true')
    
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
  
  const handleGridStatsTimePeriodChange = (event) => {
    const newPeriod = event.target.value
    setGridStatsTimePeriod(newPeriod)
    localStorage.setItem('carboniq_grid_time_period', newPeriod)
  }
  
  const handleIntervSummaryTimePeriodChange = (event) => {
    const newPeriod = event.target.value
    setIntervSummaryTimePeriod(newPeriod)
    localStorage.setItem('carboniq_interv_time_period', newPeriod)
  }
  
  const handleConvHistoryTimePeriodChange = (index, newPeriod) => {
    setConversationHistory(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], timePeriod: newPeriod }
      return updated
    })
  }
  
  // Draggable sidebar handlers
  const handleMouseDown = (e) => {
    if (!isHistoryExpanded) return // Only allow drag when expanded
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
        right: 'auto',
        transform: 'none'
      })
    }
    
    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false)
        // Save position
        localStorage.setItem('carboniq_sidebar_position_expanded', JSON.stringify(sidebarPosition))
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

  // Handle Esc key to minimize the history panel
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === 'Escape' && isHistoryExpanded) {
        // Save position before minimizing
        localStorage.setItem('carboniq_sidebar_position_expanded', JSON.stringify(sidebarPosition))
        setIsHistoryExpanded(false)
      }
    }

    document.addEventListener('keydown', handleEscKey)
    return () => document.removeEventListener('keydown', handleEscKey)
  }, [isHistoryExpanded, sidebarPosition])

  // Toggle history expansion
  const toggleHistoryExpansion = () => {
    if (isHistoryExpanded) {
      // Save position before minimizing
      localStorage.setItem('carboniq_sidebar_position_expanded', JSON.stringify(sidebarPosition))
    }
    setIsHistoryExpanded(!isHistoryExpanded)
  }
  
  const loadBaseline = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/baseline')
      if (!response.ok) throw new Error('Failed to fetch baseline data')
      
      const data = await response.json()
      setBaseline(data.grid)
      setBaselineMetadata(data.metadata)
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

      // Debug: Log both intervention and statistics to console
      console.log('[CARBONIQ] Intervention received:', {
        reduction_percent: interventionData?.reduction_percent,
        magnitude_percent: interventionData?.magnitude_percent,
        direction: interventionData?.direction,
        description: interventionData?.description,
        confidence_level: interventionData?.confidence_level
      })
      console.log('[CARBONIQ] Statistics received:', {
        is_increase: statisticsData?.is_increase,
        is_unrelated: statisticsData?.is_unrelated,
        direction: statisticsData?.direction,
        percentage_reduction: statisticsData?.percentage_reduction,
        annual_savings_tons_co2: statisticsData?.annual_savings_tons_co2,
        baseline_tons_co2: statisticsData?.baseline_tons_co2
      })
      
      // Ensure statistics has required fields
      if (!statisticsData) {
        console.warn('[CARBONIQ] No statistics data received from backend')
      }
      
      // Calculate actual overall percentage change from grid averages
      const simStats = computeStats(simulationData)
      setSimulationStats(simStats) // Store simulation stats separately for persistent display
      const actualOverallChangePercent = baselineAverage && simStats
        ? ((baselineAverage - simStats.avgValue) / baselineAverage) * 100
        : 0
      
      // Calculate actual total emissions saved based on grid data
      // IMPORTANT: Use baselineMetadata (not simulation metadata) for accurate baseline
      const baselineTotalAnnual = baselineMetadata?.annual_emissions_tonnes || 0
      const actualAnnualSavings = baselineTotalAnnual * (actualOverallChangePercent / 100)
      
      // Add to conversation history
      const newConversation = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        prompt: prompt,
        simulation: simulationData,
        intervention: interventionData,
        statistics: statisticsData,
        actualOverallChangePercent: actualOverallChangePercent, // Store actual calculated change
        actualAnnualSavings: actualAnnualSavings, // Store actual savings in tonnes/year
        view: 'simulation',
        timePeriod: 'annual' // Initialize with default time period
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
    setSimulationStats(computeStats(conversation.simulation)) // Recompute stats from stored simulation
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
      setSimulationStats(null)
      setIntervention(null)
      setStatistics(null)
      setCurrentView('baseline')
      // Reset position to bottom-left corner and minimize
      localStorage.removeItem('carboniq_sidebar_position_expanded')
      setSidebarPosition({ bottom: '2rem', left: '2rem' })
      setIsHistoryExpanded(false) // Minimize the card
    }
  }
  
  const deleteConversation = (index, event) => {
    event.stopPropagation() // Prevent triggering the card click

    const newHistory = conversationHistory.filter((_, i) => i !== index)
    setConversationHistory(newHistory)

    // If this was the last conversation, reset position and minimize
    if (newHistory.length === 0) {
      localStorage.removeItem('carboniq_sidebar_position_expanded')
      setSidebarPosition({ bottom: '2rem', left: '2rem' })
      setIsHistoryExpanded(false) // Minimize the card
    }

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
        setSimulationStats(null)
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

  // Store baseline average when baseline data loads
  useEffect(() => {
    if (baseline && baseline.length > 0) {
      const baselineStats = computeStats(baseline)
      if (baselineStats) {
        setBaselineAverage(baselineStats.avgValue)
      }
    }
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

  // For Grid Statistics display: use appropriate data based on view
  const displayStats = useMemo(() => {
    if (currentView === 'baseline') {
      return computeStats(baseline)
    } else if ((currentView === 'simulation' || currentView === 'difference') && simulation) {
      return computeStats(simulation)
    }
    return stats
  }, [currentView, baseline, simulation, stats])

  const getMarkerColor = useCallback((value, view) => {
    if (view === 'difference') {
      if (value > 25) return '#10b981'  // High - Darker green
      if (value > 10) return '#86efac'  // Medium - Light green
      if (value > 0) return '#fde047'   // Low - Yellow
      return '#fb923c'                  // No Significant Reduction - Orange
    }

    // Use ACTUAL emission values (tonnes CO₂/km²/day) to match legend
    // NYC inventory-aligned ranges (6-tier system for better color distribution):
    // Peak Hotspots: >500 (airports)
    // High: 150-500 (dense Manhattan commercial)
    // Medium-High: 85-150 (above average, commercial areas)
    // Medium: 50-85 (around citywide average ~64.7)
    // Medium-Low: 25-50 (below average)
    // Low: <25 (parks, water, outer areas)

    if (value > 500) return 'rgba(109, 40, 217, 0.9)'  // Peak Hotspots - Dark Purple
    if (value > 150) return 'rgba(153, 27, 27, 0.9)'   // High - Very Dark Crimson red
    if (value > 85) return 'rgba(239, 68, 68, 0.8)'    // Medium-High - Red
    if (value > 50) return 'rgba(249, 115, 22, 0.7)'   // Medium - Orange
    if (value > 25) return 'rgba(250, 204, 21, 0.7)'   // Medium-Low - Yellow
    return 'rgba(34, 197, 94, 0.7)'                    // Low - Green
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
      {/* Conversation History - Minimized Pill (Bottom-left) */}
      {conversationHistory.length > 0 && !isHistoryExpanded && (
        <button
          className="history-pill glass"
          onClick={toggleHistoryExpansion}
          title="Open conversation history (Esc to close)"
          aria-label={`Open conversation history. ${conversationHistory.length} conversation${conversationHistory.length > 1 ? 's' : ''}`}
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="history-pill-count">{conversationHistory.length}</span>
          <span className="history-pill-text">History</span>
        </button>
      )}

      {/* Conversation History - Expanded Card/Panel (Overlay) */}
      {conversationHistory.length > 0 && isHistoryExpanded && (
        <aside
          ref={sidebarRef}
          className={`conversation-card glass ${isDragging ? 'dragging' : ''}`}
          style={sidebarPosition}
          onMouseDown={handleMouseDown}
          role="dialog"
          aria-label="Conversation history"
          aria-modal="false"
        >
          <div className="conversation-card-header" style={{ cursor: 'move' }}>
            <div className="conversation-header-title" style={{ flex: 1, cursor: 'move' }}>
              <span className="drag-handle" title="Drag to move" style={{ cursor: 'move', fontSize: '18px', marginRight: '8px' }} aria-hidden="true">⋮⋮</span>
              <h2 className="sidebar-title" style={{ cursor: 'move' }}>Conversation History</h2>
            </div>
            <div className="conversation-header-controls" style={{ display: 'flex', gap: '6px' }}>
              <button
                className="header-control-btn minimize-btn"
                onClick={(e) => { e.stopPropagation(); setIsHistoryExpanded(false); }}
                title="Minimize (Esc)"
                aria-label="Minimize conversation history"
                style={{ cursor: 'pointer' }}
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="16" height="16">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          <div className="conversation-list" role="list">
            {conversationHistory.map((conv, index) => (
              <div
                key={conv.id}
                className={`conversation-item ${activeConversationIndex === index ? 'active' : ''}`}
                onClick={() => loadConversation(index)}
                role="listitem"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    loadConversation(index)
                  }
                }}
                aria-label={`Conversation ${index + 1}: ${conv.prompt}`}
              >
                <button
                  className="delete-conversation-btn"
                  onClick={(e) => deleteConversation(index, e)}
                  title="Delete this conversation"
                  aria-label={`Delete conversation ${index + 1}`}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
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
                    {conv.statistics?.is_unrelated || Math.abs(conv.actualOverallChangePercent || 0) === 0 ? (
                      <>
                        <span className="stat-badge neutral">0.0%</span>
                        <span className="stat-value neutral">{conv.statistics?.is_unrelated ? 'No climate impact' : 'No Significant Reduction'}</span>
                      </>
                    ) : (
                      <>
                        <span className={`stat-badge ${(() => {
                          const percent = conv.actualOverallChangePercent;
                          if (percent < 0) return 'increase'; // Negative = emissions increased (red)
                          if (percent > 25) return 'high-reduction'; // >25% = high reduction (dark green)
                          if (percent > 10) return 'medium-reduction'; // 10-25% = medium reduction (medium green)
                          return 'low-reduction'; // 0-10% = low reduction (light green)
                        })()}`}>
                          {Math.abs(conv.actualOverallChangePercent || 0) === 0 ? '0.0' : `${conv.actualOverallChangePercent < 0 ? '+' : '−'}${Math.abs(conv.actualOverallChangePercent || 0).toFixed(1)}`}%
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span className={`stat-value ${conv.actualOverallChangePercent < 0 ? 'increase' : 'decrease'}`}>
                            {conv.actualOverallChangePercent < 0
                              ? `${formatEmissionsWithPeriod(Math.abs(conv.actualAnnualSavings || 0), unitSystem, conv.timePeriod || 'annual', true)} added`
                              : `${formatEmissionsWithPeriod(Math.abs(conv.actualAnnualSavings || 0), unitSystem, conv.timePeriod || 'annual', true)} saved`
                            }
                          </span>
                          <select 
                            value={conv.timePeriod || 'annual'} 
                            onChange={(e) => {
                              e.stopPropagation();
                              handleConvHistoryTimePeriodChange(index, e.target.value);
                            }}
                            onMouseDown={(e) => e.stopPropagation()}
                            style={{ 
                              fontSize: '0.6rem', 
                              padding: '0.1rem 0.25rem', 
                              borderRadius: '3px',
                              border: '1px solid rgba(255,255,255,0.3)',
                              background: 'rgba(17, 24, 39, 0.8)',
                              color: 'rgba(255, 255, 255, 0.9)',
                              cursor: 'pointer'
                            }}
                          >
                            <option value="daily" style={{ background: '#1f2937', color: '#fff' }}>Daily</option>
                            <option value="annual" style={{ background: '#1f2937', color: '#fff' }}>Annual</option>
                          </select>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </aside>
      )}
      
      {/* Premium Header with Logo */}
      <header className="header premium-header slide-in-down">
        <div className="header-content">
          <div className="header-left">
            <Logo size="large" />
            <div className="header-text">
              <h1 className="title">CarbonIQ</h1>
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
            
            <div className="unit-selector glass-morphism" title={unitSystem === 'metric' ? '1 tonne = 1,000 kg' : '1 ton = 2,000 lbs'} style={{ cursor: 'help', padding: '0.5rem 0.75rem' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span style={{ fontSize: '0.95rem', marginLeft: '0.3rem', whiteSpace: 'nowrap', fontWeight: '500' }}>
                {unitSystem === 'metric' ? '1 tonne = 1,000 kg' : '1 ton = 2,000 lbs'}
              </span>
            </div>
            
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="main-content fade-in">
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
            <h2 className="section-title">
              Emissions Visualization 
              <span style={{ fontSize: '1.1rem', fontWeight: '400', opacity: 0.8, marginLeft: '0.5rem' }}>
                ({unitSystem === 'imperial' ? 'CO₂/mi²/day' : 'CO₂/km²/day'})
              </span>
            </h2>
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
                    <span>High (&gt;25%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#86efac'}}></div>
                    <span>Medium (10-25%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#fde047'}}></div>
                    <span>Low (0-10%)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{background: '#fb923c'}}></div>
                    <span>No Significant Reduction</span>
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
      {(displayStats || statistics) && (
        <div className="stats-section fade-in">
          {displayStats && (
            <div className="stat-card glass">
              <h3 className="stat-card-title">Grid Statistics</h3>
              <p style={{ fontSize: '0.85rem', opacity: 0.8, marginBottom: '1rem', lineHeight: '1.4' }}>
                {baselineMetadata ? (
                  <>
                    Coverage: ~{unitSystem === 'imperial' 
                      ? `${Math.round(baselineMetadata.coverage_area_km2 * 0.386102)} mi²` 
                      : `${Math.round(baselineMetadata.coverage_area_km2)} km²`} (NYC boundaries).{' '}
                    {baselineMetadata.datapoints.toLocaleString()} datapoints, each ~{baselineMetadata.cell_area_km2.toFixed(2)} km².{' '}
                    Calibrated to NYC GHG inventory (~{
                      unitSystem === 'imperial'
                        ? `${((baselineMetadata.annual_emissions_tonnes * 1.10231131) / 1_000_000).toFixed(1)}M tons/year`
                        : `${(baselineMetadata.annual_emissions_tonnes / 1_000_000).toFixed(1)}M tonnes/year`
                    }).
                  </>
                ) : (
                  <>
                    Calibrated to NYC GHG inventory benchmarks.
                  </>
                )}
              </p>
              <div className="stat-grid" style={{ gridTemplateColumns: intervention?.grid_impact?.affected_area_km2 ? 'repeat(2, 1fr)' : 'repeat(2, 1fr)' }}>
                <div className="stat-item">
                  <span className="stat-label" style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                    Average Intensity (per {unitSystem === 'imperial' ? 'mi²' : 'km²'}/day)
                    {intervention?.grid_impact && (
                      <span className="stat-sublabel"> (Baseline)</span>
                    )}
                  </span>
                  <span className="stat-value" style={{ fontSize: '1.2rem', fontWeight: '700' }}>{formatEmissionIntensity((displayStats?.avgValue) || 0, unitSystem)}</span>
                  {intervention?.grid_impact && (
                    <>
                      <span className="stat-sublabel">After Intervention</span>
                      <span className="stat-value-secondary">
                        {formatEmissionIntensity(intervention.grid_impact.reduced_avg_intensity || 0, unitSystem)}
                        <span className={`stat-change ${intervention.grid_impact.avg_change_percent < 0 ? 'increase' : 'decrease'}`}>
                          {intervention.grid_impact.avg_change_percent > 0 ? '−' : '+'}{Math.abs(intervention.grid_impact.avg_change_percent || 0).toFixed(1)}%
                        </span>
                      </span>
                    </>
                  )}
                </div>
                <div className="stat-item">
                  <span className="stat-label" style={{ fontSize: '0.9rem', fontWeight: '600' }}>Data Points</span>
                  <span className="stat-value" style={{ fontSize: '1.2rem', fontWeight: '700' }}>{displayStats?.dataPoints?.toLocaleString() || '0'}</span>
                </div>
                {baselineMetadata && (
                  <div className="stat-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gridColumn: '1 / -1' }}>
                    <span className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center', fontSize: '0.95rem', fontWeight: '600' }}>
                      <span>Total Citywide</span>
                      <select 
                        value={gridStatsTimePeriod} 
                        onChange={handleGridStatsTimePeriodChange} 
                        style={{ 
                          fontSize: '0.7rem', 
                          padding: '0.15rem 0.3rem', 
                          borderRadius: '4px',
                          border: '1px solid rgba(255,255,255,0.3)',
                          background: 'rgba(17, 24, 39, 0.8)',
                          color: 'rgba(255, 255, 255, 0.9)',
                          cursor: 'pointer'
                        }}
                      >
                        <option value="daily" style={{ background: '#1f2937', color: '#fff' }}>Daily</option>
                        <option value="annual" style={{ background: '#1f2937', color: '#fff' }}>Annual</option>
                      </select>
                      {currentView === 'simulation' && (
                        <span className="stat-sublabel"> (Baseline)</span>
                      )}
                    </span>
                    <span className="stat-value" style={{ fontSize: '1.3rem', fontWeight: '700', marginTop: '0.4rem' }}>
                      {formatEmissionsWithPeriod(
                        baselineMetadata.annual_emissions_tonnes || 0,
                        unitSystem,
                        gridStatsTimePeriod,
                        true
                      )}
                    </span>
                    {currentView === 'simulation' && baselineAverage && displayStats && (
                      <>
                        <span className="stat-sublabel" style={{ fontSize: '0.85rem', marginTop: '0.6rem' }}>After Intervention</span>
                        <span className="stat-value-secondary" style={{ fontSize: '1.15rem', fontWeight: '600', marginTop: '0.2rem' }}>
                          {(() => {
                            const percentChange = ((baselineAverage - displayStats.avgValue) / baselineAverage) * 100
                            const simulatedTotal = baselineMetadata.annual_emissions_tonnes * (1 - percentChange / 100)
                            return formatEmissionsWithPeriod(
                              simulatedTotal,
                              unitSystem,
                              gridStatsTimePeriod,
                              true
                            )
                          })()}
                        </span>
                      </>
                    )}
                  </div>
                )}
                {intervention?.grid_impact?.affected_area_km2 && (
                  <div className="stat-item">
                    <span className="stat-label">Affected Area</span>
                    <span className="stat-value">{
                      unitSystem === 'imperial' 
                        ? `${(intervention.grid_impact.affected_area_km2 * 0.386102).toFixed(1)} mi²`
                        : `${intervention.grid_impact.affected_area_km2.toFixed(1)} km²`
                    }</span>
                  </div>
                )}
              </div>
              {intervention?.grid_impact?.notes && (
                <p style={{ fontSize: '0.8rem', opacity: 0.7, marginTop: '0.75rem', fontStyle: 'italic' }}>
                  {intervention.grid_impact.notes}
                </p>
              )}
            </div>
          )}

          {intervention && (
            <div className="stat-card glass">
              <h3 className="stat-card-title">Intervention Summary</h3>

              {/* Brief summary */}
              <div style={{ marginBottom: '0.85rem', padding: '0.65rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '8px', borderLeft: '3px solid rgb(99, 102, 241)' }}>
                <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.5', fontWeight: '500' }}>{intervention.description}</p>
              </div>

              {/* Average change percentage - calculated from actual grid data */}
              {baselineAverage && simulationStats && baselineMetadata && (
                <div style={{ marginBottom: '0.85rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', fontWeight: '600' }}>Overall Citywide Impact</span>
                    {(() => {
                      // Calculate actual percentage change from grid averages (always baseline vs simulation)
                      const percentChange = ((baselineAverage - simulationStats.avgValue) / baselineAverage) * 100
                      const absPercent = Math.abs(percentChange)
                      const isZero = absPercent < 0.05 // Treat anything < 0.05% as 0
                      const isIncrease = percentChange < 0
                      
                      if (isZero) {
                        return (
                          <span className="stat-value" style={{ fontSize: '1.35rem', fontWeight: '700', color: 'var(--text-muted)' }}>
                            0.0%
                          </span>
                        )
                      }
                      
                      return (
                        <span className={`stat-value ${isIncrease ? 'increase' : 'decrease'}`} style={{ fontSize: '1.35rem', fontWeight: '700' }}>
                          {isIncrease ? '+' : '−'}{absPercent.toFixed(1)}%
                        </span>
                      )
                    })()}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontWeight: '500' }}>
                    <span>
                      {(() => {
                        const percentChange = ((baselineAverage - simulationStats.avgValue) / baselineAverage) * 100
                        const actualSavings = baselineMetadata.annual_emissions_tonnes * (percentChange / 100)
                        const isIncrease = percentChange < 0
                        return isIncrease
                          ? `${formatEmissionsWithPeriod(Math.abs(actualSavings), unitSystem, intervSummaryTimePeriod, true)} added`
                          : `${formatEmissionsWithPeriod(Math.abs(actualSavings), unitSystem, intervSummaryTimePeriod, true)} saved`
                      })()}
                    </span>
                    <select 
                      value={intervSummaryTimePeriod} 
                      onChange={handleIntervSummaryTimePeriodChange} 
                      style={{ 
                        fontSize: '0.65rem', 
                        padding: '0.15rem 0.3rem', 
                        borderRadius: '4px',
                        border: '1px solid rgba(255,255,255,0.3)',
                        background: 'rgba(17, 24, 39, 0.8)',
                        color: 'rgba(255, 255, 255, 0.9)',
                        cursor: 'pointer'
                      }}
                    >
                      <option value="daily" style={{ background: '#1f2937', color: '#fff' }}>Daily</option>
                      <option value="annual" style={{ background: '#1f2937', color: '#fff' }}>Annual</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Expandable calculations & analysis */}
              {intervention.reasoning && (
                <details style={{ marginTop: '0.85rem' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '0.875rem', fontWeight: '600', color: 'var(--text-primary)', padding: '0.4rem 0' }}>
                    Calculations & Analysis
                  </summary>
                  <div style={{ marginTop: '0.6rem', padding: '0.65rem', background: 'rgba(17, 24, 39, 0.3)', borderRadius: '6px', fontSize: '0.85rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                    {baselineAverage && simulationStats && (
                      <div style={{ marginBottom: '0.75rem', padding: '0.5rem', background: 'rgba(99, 102, 241, 0.15)', borderRadius: '4px', borderLeft: '3px solid rgb(99, 102, 241)' }}>
                        <strong>Grid Analysis:</strong> Based on spatial modeling, this intervention results in approximately{' '}
                        <strong style={{ color: 'var(--text-primary)' }}>
                          {Math.abs(((baselineAverage - simulationStats.avgValue) / baselineAverage) * 100).toFixed(1)}%
                        </strong>{' '}
                        {((baselineAverage - simulationStats.avgValue) / baselineAverage) < 0 ? 'citywide baseline increase' : 'citywide baseline decrease'}.
                      </div>
                    )}
                    {intervention.reasoning}
                  </div>

                  {/* Secondary impacts inside calculations section */}
                  {intervention.secondary_impacts && intervention.secondary_impacts.length > 0 && (
                    <div style={{ marginTop: '0.85rem' }}>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
                        Secondary Impacts
                      </h4>
                      <ul style={{ marginTop: '0.4rem', marginBottom: 0, paddingLeft: '1.5rem', fontSize: '0.85rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                        {intervention.secondary_impacts.map((impact, i) => (
                          <li key={i} style={{ marginBottom: '0.5rem' }}>{impact}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </details>
              )}
            </div>
          )}
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

      {/* Footer */}
      <footer style={{
        width: '100%',
        padding: '1rem 2rem',
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(10px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
        lineHeight: '1.4',
        boxSizing: 'border-box'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>Powered by:</span>
          <span>Claude API (Anthropic)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: '600', color: 'var(--text-secondary)', flexShrink: 0 }}>Data Sources:</span>
          <span style={{ lineHeight: '1.5' }}>
            NYC Open Data, Port Authority of NY & NJ, FAA, EPA, ICAO, NYISO, Con Edison, NYC DEP, NY DMV, NYC TLC, MTA
          </span>
        </div>
      </footer>
    </div>
  )
}

export default App
