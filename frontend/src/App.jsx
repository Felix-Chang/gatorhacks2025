import { useState, useEffect } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

function App() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [baseline, setBaseline] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [intervention, setIntervention] = useState(null)
  const [error, setError] = useState(null)
  const [currentView, setCurrentView] = useState('baseline')
  const [aiAnalysis, setAiAnalysis] = useState(null)

  useEffect(() => {
    loadBaseline()
  }, [])

  const loadBaseline = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/baseline')
      if (!response.ok) throw new Error('Failed to fetch baseline data')
      
      const data = await response.json()
      setBaseline(data.grid)
    } catch (error) {
      console.error('Error loading baseline:', error)
      setError('Failed to load baseline data. Make sure backend is running.')
    }
  }

  const handleSimulate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post('http://localhost:8000/api/simulate', { prompt })
      setSimulation(res.data.grid)
      setIntervention(res.data.intervention)
      if (res.data.ai_analysis) {
        setAiAnalysis(res.data.ai_analysis)
      }
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  const setPromptFromExample = (examplePrompt) => {
    setPrompt(examplePrompt)
  }

  const getMapData = () => {
    switch (currentView) {
      case 'baseline':
        return baseline
      case 'simulation':
        return simulation
      case 'difference':
        if (!baseline || !simulation) return null
        return baseline.map((baselinePoint, index) => {
          const simPoint = simulation[index]
          const reduction = baselinePoint.value - simPoint.value
          const reductionPercent = (reduction / baselinePoint.value) * 100
          return {
            lat: baselinePoint.lat,
            lon: baselinePoint.lon,
            value: reductionPercent,
            baselineValue: baselinePoint.value,
            simulationValue: simPoint.value
          }
        })
      default:
        return baseline
    }
  }

  const getMarkerColor = (value, view) => {
    if (view === 'difference') {
      if (value > 50) return '#00ff00'
      if (value > 25) return '#88ff00'
      if (value > 10) return '#ffff00'
      if (value > 0) return '#ff8800'
      return '#ff0000'
    }
    
    // For baseline and simulation views
    const maxValue = Math.max(...(baseline?.map(p => p.value) || [0]))
    const normalizedIntensity = value / maxValue
    
    if (normalizedIntensity > 0.8) return '#ff4444'
    if (normalizedIntensity > 0.6) return '#ff8844'
    if (normalizedIntensity > 0.4) return '#ffaa44'
    if (normalizedIntensity > 0.2) return '#88ff44'
    return '#44ff44'
  }

  const calculateStats = (data) => {
    if (!data) return null
    
    const values = data.map(point => point.value)
    const minValue = Math.min(...values)
    const maxValue = Math.max(...values)
    const avgValue = values.reduce((a, b) => a + b, 0) / values.length
    const totalEmissions = values.reduce((a, b) => a + b, 0)
    const medianValue = values.sort((a, b) => a - b)[Math.floor(values.length / 2)]
    
    return {
      minValue,
      maxValue,
      avgValue,
      totalEmissions,
      medianValue,
      dataPoints: values.length
    }
  }

  const mapData = getMapData()
  const stats = calculateStats(mapData)

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <h1 className="title">🌍 NYC CO₂ Emissions Simulator 🌱</h1>
        <p>🌿 Advanced AI-Powered Environmental Impact Analysis 🌿</p>
        
        <div className="status-bar">
          <div className="status-indicator status-success">
            <i className="fas fa-check-circle"></i>
            <span>🌐 Backend Connected</span>
          </div>
          <div className="status-indicator status-success">
            <i className="fas fa-database"></i>
            <span>🌍 Real Data Sources</span>
          </div>
          <div className="status-indicator status-success">
            <i className="fas fa-brain"></i>
            <span>🤖 AI Analysis Active</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Control Panel */}
        <div className="control-panel">
          <h2>🌿 Simulation Controls 🌿</h2>
          
          <div className="input-group">
            <label htmlFor="promptInput">🌱 Environmental Intervention Prompt 🌱</label>
            <textarea 
              id="promptInput"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe your environmental intervention..."
              disabled={loading}
            />
          </div>
          
          <button className="btn btn-primary" onClick={handleSimulate} disabled={loading || !prompt.trim()}>
            <i className="fas fa-play"></i>
            🚀 Run Simulation
          </button>
          
          <button className="btn btn-secondary" onClick={loadBaseline}>
            <i className="fas fa-chart-line"></i>
            📊 Load Baseline
          </button>
          
          <div className="example-prompts">
            <h3>💡 Example Prompts 💡</h3>
            <div className="prompt-example" onClick={() => setPromptFromExample('Convert 30% of Manhattan taxis to electric vehicles')}>
              🚗 Convert 30% of Manhattan taxis to electric vehicles
            </div>
            <div className="prompt-example" onClick={() => setPromptFromExample('Install solar panels on 50% of Brooklyn buildings')}>
              ☀️ Install solar panels on 50% of Brooklyn buildings
            </div>
            <div className="prompt-example" onClick={() => setPromptFromExample('Reduce industrial emissions by 25% in Queens')}>
              🏭 Reduce industrial emissions by 25% in Queens
            </div>
            <div className="prompt-example" onClick={() => setPromptFromExample('Implement green roofs on 40% of Bronx buildings')}>
              🌿 Implement green roofs on 40% of Bronx buildings
            </div>
            <div className="prompt-example" onClick={() => setPromptFromExample('Convert Staten Island buses to electric')}>
              🚌 Convert Staten Island buses to electric
            </div>
          </div>
        </div>

        {/* Map Container */}
        <div className="map-container">
          <div className="map-header">
            <h2>🗺️ NYC Emissions Map 🌍</h2>
            <div className="map-controls">
              <button 
                className={`map-btn ${currentView === 'baseline' ? 'active' : ''}`}
                onClick={() => setCurrentView('baseline')}
              >
                📊 Baseline
              </button>
              <button 
                className={`map-btn ${currentView === 'simulation' ? 'active' : ''}`}
                onClick={() => setCurrentView('simulation')}
                disabled={!simulation}
              >
                🎯 Simulation
              </button>
              <button 
                className={`map-btn ${currentView === 'difference' ? 'active' : ''}`}
                onClick={() => setCurrentView('difference')}
                disabled={!baseline || !simulation}
              >
                📈 Impact
              </button>
            </div>
          </div>
          
          <div className="map-wrapper">
            <MapContainer center={[40.7128, -74.0060]} zoom={11} className="map">
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='© OpenStreetMap contributors'
              />
              
              {mapData && mapData.map((point, index) => (
                <CircleMarker
                  key={index}
                  center={[point.lat, point.lon]}
                  radius={currentView === 'difference' ? 5 : 8}
                  pathOptions={{
                    fillColor: getMarkerColor(point.value, currentView),
                    color: getMarkerColor(point.value, currentView),
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: 0.6
                  }}
                >
                  <Popup>
                    <div className="popup-content">
                      <h4>{currentView === 'baseline' ? 'Baseline Emissions' : 
                           currentView === 'simulation' ? 'Simulation Results' : 
                           'Impact Difference'}</h4>
                      <p><strong>Location:</strong> {point.lat.toFixed(4)}, {point.lon.toFixed(4)}</p>
                      {currentView === 'difference' ? (
                        <>
                          <p><strong>Reduction:</strong> {point.value.toFixed(1)}%</p>
                          <p><strong>Before:</strong> {point.baselineValue.toFixed(2)} kg CO₂/km²/day</p>
                          <p><strong>After:</strong> {point.simulationValue.toFixed(2)} kg CO₂/km²/day</p>
                        </>
                      ) : (
                        <p><strong>Emissions:</strong> {point.value.toFixed(2)} kg CO₂/km²/day</p>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
          
          <div className="legend">
            <h3>ℹ️ Map Legend ℹ️</h3>
            {currentView === 'difference' ? (
              <>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#00ff00'}}></div>
                  <span>🟢 High Reduction (&gt;50%)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#88ff00'}}></div>
                  <span>🟡 Medium-High Reduction (25-50%)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ffff00'}}></div>
                  <span>🟡 Medium Reduction (10-25%)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ff8800'}}></div>
                  <span>🟠 Low Reduction (0-10%)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ff0000'}}></div>
                  <span>🔴 No Reduction or Increase</span>
                </div>
              </>
            ) : (
              <>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ff4444'}}></div>
                  <span>🔴 High Emissions (&gt;1000 kg CO₂/km²/day)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ff8844'}}></div>
                  <span>🟠 Medium-High Emissions (500-1000 kg CO₂/km²/day)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#ffaa44'}}></div>
                  <span>🟡 Medium Emissions (200-500 kg CO₂/km²/day)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#88ff44'}}></div>
                  <span>🟢 Low-Medium Emissions (50-200 kg CO₂/km²/day)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color" style={{background: '#44ff44'}}></div>
                  <span>🌱 Low Emissions (&lt;50 kg CO₂/km²/day)</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      {stats && (
        <div className="stats-grid">
          <div className="stats-card fade-in">
            <h3>📊 {currentView === 'baseline' ? 'Baseline' : currentView === 'simulation' ? 'Simulation' : 'Impact'} Statistics 📊</h3>
            <div className="stat-item">
              <span className="stat-label">🌍 Total Daily Emissions</span>
              <span className="stat-value">{stats.totalEmissions.toLocaleString()} kg CO₂</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">📏 Average per km²</span>
              <span className="stat-value">{stats.avgValue.toFixed(1)} kg CO₂/km²/day</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">🔴 Peak Emissions</span>
              <span className="stat-value">{stats.maxValue.toFixed(0)} kg CO₂/km²/day</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">🟢 Minimum Emissions</span>
              <span className="stat-value">{stats.minValue.toFixed(0)} kg CO₂/km²/day</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">📈 Median Emissions</span>
              <span className="stat-value">{stats.medianValue.toFixed(1)} kg CO₂/km²/day</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">📍 Data Points</span>
              <span className="stat-value">{stats.dataPoints.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* AI Analysis */}
      {aiAnalysis && (
        <div className="ai-analysis fade-in">
          <h3>🤖 AI Analysis 🌍</h3>
          <div className="ai-content">
            <div style={{marginBottom: '15px'}}>
              <strong>Geographic Analysis:</strong> {aiAnalysis.geographic_analysis || 'Analysis not available'}
            </div>
            <div style={{marginBottom: '15px'}}>
              <strong>Spatial Reasoning:</strong> {aiAnalysis.spatial_reasoning || 'Reasoning not available'}
            </div>
            <div>
              <strong>Real-World Factors:</strong> {aiAnalysis.real_world_factors || 'Factors not available'}
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Loading Display */}
      {loading && (
        <div className="loading">
          <div className="loading-spinner"></div>
          <span>Running AI simulation...</span>
        </div>
      )}
    </div>
  )
}

export default App