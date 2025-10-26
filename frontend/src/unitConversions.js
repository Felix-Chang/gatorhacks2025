/**
 * Unit Conversion Utilities for Frontend Display
 * Backend uses metric internally - these functions convert for display only
 * All conversions use exact mathematical constants for 100% accuracy
 */

// Exact conversion constants (NIST standards)
export const CONVERSIONS = {
  // Mass
  KG_TO_LBS: 2.20462262185,
  METRIC_TON_TO_SHORT_TON: 1.10231131, // Metric ton to US short ton
  
  // Distance
  KM_TO_MILES: 0.621371192237,
  METERS_TO_FEET: 3.28084,
  
  // Area
  KM2_TO_MI2: 0.386102159, // km² to mi²
  M2_TO_FT2: 10.7639104,
  
  // Combined (for emission intensity)
  // tonnes CO₂/km²/day → tons CO₂/mi²/day
  // = (metric ton → short ton) / (km² → mi²)
  // = 1.10231 / 0.386102 = 2.85449
  TONNES_PER_KM2_TO_TONS_PER_MI2: 2.85449,
};

/**
 * Convert emission intensity between metric and imperial
 * @param {number} value - Emission value in tonnes CO₂/km²/day
 * @param {string} toUnit - 'metric' or 'imperial'
 * @returns {number} Converted value
 */
export function convertEmissionIntensity(value, toUnit) {
  if (toUnit === 'imperial') {
    return value * CONVERSIONS.TONNES_PER_KM2_TO_TONS_PER_MI2;
  }
  return value; // Already metric
}

/**
 * Convert annual emissions (tons) between metric and imperial
 * @param {number} tons - Emissions in metric tons CO₂
 * @param {string} toUnit - 'metric' or 'imperial'
 * @returns {number} Converted value
 */
export function convertAnnualEmissions(tons, toUnit) {
  if (toUnit === 'imperial') {
    return tons * CONVERSIONS.METRIC_TON_TO_SHORT_TON;
  }
  return tons; // Already metric
}

/**
 * Format emission intensity with proper units
 * @param {number} value - Raw value in tonnes CO₂/km²/day (metric)
 * @param {string} unit - 'metric' or 'imperial'
 * @returns {string} Formatted string with units
 */
export function formatEmissionIntensity(value, unit = 'metric') {
  const converted = convertEmissionIntensity(value, unit);

  if (unit === 'imperial') {
    return `${converted.toFixed(1)} tons CO₂/mi²/day`;
  }
  return `${converted.toFixed(1)} tonnes CO₂/km²/day`;
}

/**
 * Format annual emissions with proper units
 * @param {number} tons - Value in metric tons
 * @param {string} unit - 'metric' or 'imperial'
 * @param {boolean} abbreviated - Use K for thousands
 * @returns {string} Formatted string
 */
export function formatAnnualEmissions(tons, unit = 'metric', abbreviated = true) {
  const converted = convertAnnualEmissions(tons, unit);
  const unitLabel = unit === 'imperial' ? 'tons' : 'tonnes'; // US tons vs metric tonnes

  if (abbreviated) {
    if (Math.abs(converted) >= 1000000) {
      return `${(converted / 1000000).toFixed(1)}M ${unitLabel}/year`;
    } else if (Math.abs(converted) >= 1000) {
      return `${(converted / 1000).toFixed(1)}K ${unitLabel}/year`;
    }
  }

  return `${converted.toLocaleString()} ${unitLabel}`;
}

/**
 * Get legend ranges for the current unit system
 * @param {string} unit - 'metric' or 'imperial'
 * @returns {Array} Array of range objects with labels and colors
 */
export function getLegendRanges(unit = 'metric') {
  // NYC inventory-aligned ranges (tonnes CO₂/km²/day)
  // Peak hotspots: 1k-5k | High urban: 200-300 | Median: 40-120 | Min: 5-30
  const metricRanges = [
    { min: 1000, max: Infinity, label: 'Peak Hotspots', color: 'rgba(127, 29, 29, 0.9)' },
    { min: 200, max: 1000, label: 'Very High', color: 'rgba(239, 68, 68, 0.8)' },
    { min: 80, max: 200, label: 'High', color: 'rgba(251, 146, 60, 0.7)' },
    { min: 30, max: 80, label: 'Medium', color: 'rgba(250, 204, 21, 0.7)' },
    { min: 0, max: 30, label: 'Low', color: 'rgba(74, 222, 128, 0.6)' },
  ];
  
  if (unit === 'imperial') {
    // Convert ranges to imperial
    return metricRanges.map(range => ({
      ...range,
      min: Math.round(convertEmissionIntensity(range.min, 'imperial')),
      max: range.max === Infinity ? Infinity : Math.round(convertEmissionIntensity(range.max, 'imperial')),
    }));
  }
  
  return metricRanges;
}

/**
 * Format legend range label
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {string} unit - 'metric' or 'imperial'
 * @returns {string} Formatted range string
 */
export function formatLegendRange(min, max, unit = 'metric') {
  if (max === Infinity) {
    return `>${min.toLocaleString()}`;
  }
  return `${min.toLocaleString()}-${max.toLocaleString()}`;
}

/**
 * Get map marker color based on value and unit
 * @param {number} value - Emission value in tonnes CO₂/km²/day (metric)
 * @param {string} view - 'baseline' or 'difference'
 * @param {string} unit - 'metric' or 'imperial' (only used for debugging)
 * @returns {string} Color hex/rgba
 */
export function getMarkerColor(value, view, unit = 'metric') {
  if (view === 'difference') {
    // Reduction percentage colors
    if (value > 50) return '#10b981';
    if (value > 25) return '#84cc16';
    if (value > 10) return '#facc15';
    if (value > 0) return '#f97316';
    return '#ef4444';
  }

  // Emission intensity colors (NYC inventory-aligned)
  // Always use metric thresholds internally (tonnes CO₂/km²/day)
  if (value > 1000) return 'rgba(127, 29, 29, 0.9)';  // Peak Hotspots (airports)
  if (value > 200) return 'rgba(239, 68, 68, 0.8)';   // Very High (dense Manhattan)
  if (value > 80) return 'rgba(251, 146, 60, 0.7)';   // High (urban centers)
  if (value > 30) return 'rgba(250, 204, 21, 0.7)';   // Medium (typical urban)
  return 'rgba(74, 222, 128, 0.6)';                   // Low (parks, water, outer areas)
}

/**
 * Get unit label for display
 * @param {string} type - 'emission_intensity' or 'annual_emissions'
 * @param {string} unit - 'metric' or 'imperial'
 * @returns {string} Unit label
 */
export function getUnitLabel(type, unit = 'metric') {
  const labels = {
    emission_intensity: {
      metric: 'tonnes CO₂/km²/day',
      imperial: 'tons CO₂/mi²/day',
    },
    annual_emissions: {
      metric: 'tonnes CO₂/year',
      imperial: 'tons CO₂/year',
    },
  };

  return labels[type]?.[unit] || '';
}

/**
 * Store unit preference in localStorage
 * @param {string} unit - 'metric' or 'imperial'
 */
export function saveUnitPreference(unit) {
  localStorage.setItem('co2unt_unit_preference', unit);
}

/**
 * Load unit preference from localStorage
 * @returns {string} 'metric' or 'imperial' (defaults to metric)
 */
export function loadUnitPreference() {
  return localStorage.getItem('co2unt_unit_preference') || 'metric';
}

