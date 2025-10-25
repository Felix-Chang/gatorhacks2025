import React from 'react'
import './logo.css'

const Logo = ({ size = 'medium', animated = false }) => {
  const sizeClasses = {
    small: 'logo-small',
    medium: 'logo-medium',
    large: 'logo-large'
  }

  return (
    <div className={`logo-container ${sizeClasses[size]} ${animated ? 'logo-animated' : ''}`}>
      <div className="logo-badge">
        <svg viewBox="0 0 200 200" className="logo-svg">
          {/* Hexagon background */}
          <defs>
            <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          {/* Hexagon shape */}
          <polygon 
            points="100,15 175,57.5 175,142.5 100,185 25,142.5 25,57.5" 
            fill="url(#logoGradient)" 
            opacity="0.2"
            stroke="url(#logoGradient)"
            strokeWidth="2"
          />
          
          {/* CO2 molecule stylized */}
          <g filter="url(#glow)">
            {/* Carbon (C) */}
            <circle cx="100" cy="100" r="18" fill="#3b82f6" />
            <text x="100" y="108" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold">C</text>
            
            {/* Oxygen atoms (O) */}
            <circle cx="60" cy="100" r="14" fill="#10b981" />
            <text x="60" y="106" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">O</text>
            
            <circle cx="140" cy="100" r="14" fill="#10b981" />
            <text x="140" y="106" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">O</text>
            
            {/* Bonds */}
            <line x1="78" y1="100" x2="82" y2="100" stroke="#64748b" strokeWidth="2" />
            <line x1="118" y1="100" x2="126" y2="100" stroke="#64748b" strokeWidth="2" />
          </g>
        </svg>
      </div>
      <div className="logo-text">
        <span className="logo-co">CO</span>
        <span className="logo-subscript">2</span>
        <span className="logo-unt">UNT</span>
      </div>
    </div>
  )
}

export default Logo

