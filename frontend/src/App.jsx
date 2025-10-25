import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [baseline, setBaseline] = useState(null)
  const [simulated, setSimulated] = useState(null)
  const [intervention, setIntervention] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/baseline')
      .then(res => res.json())
      .then(data => setBaseline(data))
      .catch(err => console.error('Baseline fetch error:', err))
  }, [])

  const handleSimulate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post('http://localhost:8000/api/simulate', { prompt })
      setSimulated(res.data)
      setIntervention(res.data.intervention)
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <div className="app">
      <div className="header">
        <h1 className="title">ðŸŒ NYC COâ‚‚ Sustainability Simulation</h1>
        <p>AI-powered climate action visualization for New York City</p>
      </div>
      
      <div className="content">
        <h2>Try a Sustainability Action</h2>
        <input
          type="text"
          className="input-box"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., Convert 30% of taxis to EVs in Manhattan"
          disabled={loading}
        />
        <button className="button" onClick={handleSimulate} disabled={loading || !prompt.trim()}>
          {loading ? 'Simulating...' : 'ðŸš€ Simulate Impact'}
        </button>

        {error && (
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {baseline && (
          <div className="result">
            <strong>âœ… Baseline Loaded:</strong> {baseline.grid.length} emission data points for NYC
          </div>
        )}

        {intervention && (
          <div className="result">
            <h3>Simulation Result:</h3>
            <p><strong>Location:</strong> {intervention.borough}</p>
            <p><strong>Sector:</strong> {intervention.sector}</p>
            <p><strong>Reduction:</strong> {intervention.reduction_percent}% emissions</p>
            <p><strong>Description:</strong> {intervention.description}</p>
          </div>
        )}

        <div style={{marginTop: '20px', padding: '20px', background: '#f3f4f6', borderRadius: '8px'}}>
          <h3>Example Prompts:</h3>
          <ul style={{marginLeft: '20px', lineHeight: '1.8'}}>
            <li>Convert 30% of taxis to EVs in Manhattan</li>
            <li>Add solar panels to 50% of Brooklyn buildings</li>
            <li>Reduce citywide industrial emissions by 20%</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default App
