import React from 'react'
import logoImage from './assets/carboniq-logo.png'

const Logo = ({ size = 'medium' }) => {
  const sizeMap = {
    small: '64px',
    medium: '80px',
    large: '102px',
    xlarge: '180px',
    xxlarge: '384px'
  }

  return (
    <img 
      src={logoImage} 
      alt="CarbonIQ Logo" 
      style={{ 
        width: sizeMap[size], 
        height: sizeMap[size],
        objectFit: 'contain'
      }} 
    />
  )
}

export default Logo

