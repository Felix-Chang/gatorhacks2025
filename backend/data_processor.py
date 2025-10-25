"""
Data Processing Module
Handles fetching, processing, and caching of NYC emissions data
"""

import numpy as np
import requests
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
import json


class NYCEmissionsData:
    """
    Manages NYC emissions data from multiple sources:
    - OpenAQ API for real-time air quality
    - Synthetic gridded emissions based on NYC geography
    """
    
    # NYC bounding box
    BOUNDS = {
        'south': 40.49,
        'north': 40.92,
        'west': -74.26,
        'east': -73.70
    }
    
    # Borough polygons (simplified center points and radius for calculation)
    BOROUGHS = {
        'Manhattan': {'center': (40.7831, -73.9712), 'intensity': 1.5},
        'Brooklyn': {'center': (40.6782, -73.9442), 'intensity': 1.2},
        'Queens': {'center': (40.7282, -73.7949), 'intensity': 1.0},
        'Bronx': {'center': (40.8448, -73.8648), 'intensity': 1.1},
        'Staten Island': {'center': (40.5795, -74.1502), 'intensity': 0.7}
    }
    
    def __init__(self, grid_resolution=50):
        """
        Initialize with specified grid resolution
        
        Args:
            grid_resolution: Number of points per dimension (50 = 2500 grid points)
        """
        self.grid_resolution = grid_resolution
        self.baseline_cache = None
        self.last_update = None
        self.openaq_cache = None
        
        # Generate baseline on initialization
        self._generate_baseline()
    
    def _generate_baseline(self):
        """
        Generate a realistic baseline emissions grid for NYC
        
        Combines:
        - Real OpenAQ station data
        - Population density proxy
        - Traffic patterns (higher in Manhattan)
        - Waterways (lower emissions)
        """
        print("[INFO] Generating baseline NYC emissions grid...")
        
        # Create lat/lon grid
        lats = np.linspace(self.BOUNDS['south'], self.BOUNDS['north'], self.grid_resolution)
        lons = np.linspace(self.BOUNDS['west'], self.BOUNDS['east'], self.grid_resolution)
        
        # Initialize emissions grid
        emissions_grid = np.zeros((self.grid_resolution, self.grid_resolution))
        
        # Generate emissions based on proximity to borough centers
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                emission_value = self._calculate_emission_at_point(lat, lon)
                emissions_grid[i, j] = emission_value
        
        # Add noise for realism
        noise = np.random.normal(0, 5, emissions_grid.shape)
        emissions_grid += noise
        emissions_grid = np.maximum(emissions_grid, 0)  # No negative emissions
        
        # Try to incorporate OpenAQ data
        try:
            openaq_data = self.fetch_openaq_data()
            if openaq_data:
                emissions_grid = self._blend_openaq_data(emissions_grid, lats, lons, openaq_data)
        except Exception as e:
            print(f"[WARN]  Could not fetch OpenAQ data: {e}")
            print("[DATA] Using synthetic baseline only")
        
        # Cache the baseline
        self.baseline_cache = (lats, lons, emissions_grid)
        self.last_update = datetime.now()
        
        print(f"[OK] Baseline generated: {self.grid_resolution}x{self.grid_resolution} grid")
        print(f"[STAT] Emission range: {emissions_grid.min():.1f} - {emissions_grid.max():.1f} kg COâ‚‚/kmÂ²/day")
    
    def _calculate_emission_at_point(self, lat: float, lon: float) -> float:
        """
        Calculate emission value at a specific point based on NYC geography
        """
        base_emission = 20.0  # Base urban emission
        
        # Calculate distance to each borough center and apply intensity
        total_intensity = 0
        for borough, data in self.BOROUGHS.items():
            center_lat, center_lon = data['center']
            intensity = data['intensity']
            
            # Euclidean distance (simplified, not geodesic)
            distance = np.sqrt((lat - center_lat)**2 + (lon - center_lon)**2)
            
            # Inverse distance weighting with falloff
            if distance < 0.1:
                contribution = intensity * 50
            else:
                contribution = intensity * 30 / (distance * 100)
            
            total_intensity += contribution
        
        # Add hotspots (airports, industrial areas)
        hotspots = [
            (40.6413, -73.7781, 30),  # JFK Airport
            (40.7769, -73.8740, 25),  # LaGuardia Airport
            (40.7580, -73.9855, 60),  # Times Square / Midtown
        ]
        
        for spot_lat, spot_lon, spot_intensity in hotspots:
            distance = np.sqrt((lat - spot_lat)**2 + (lon - spot_lon)**2)
            if distance < 0.05:
                total_intensity += spot_intensity / (distance + 0.01)
        
        # Lower emissions over water
        if self._is_over_water(lat, lon):
            total_intensity *= 0.1
        
        return base_emission + total_intensity
    
    def _is_over_water(self, lat: float, lon: float) -> bool:
        """
        Simplified check if point is over water (Hudson/East River, NY Harbor)
        """
        # Hudson River (west of Manhattan)
        if lon < -74.02 and 40.70 < lat < 40.88:
            return True
        
        # East River
        if -73.98 < lon < -73.93 and 40.70 < lat < 40.80:
            return True
        
        # New York Harbor (south)
        if lat < 40.62 and -74.05 < lon < -74.00:
            return True
        
        return False
    
    def fetch_openaq_data(self) -> List[Dict]:
        """
        Fetch real-time air quality data from OpenAQ API for NYC area
        
        Returns list of station measurements
        """
        # Check cache (cache for 1 hour)
        if self.openaq_cache and self.last_update:
            if datetime.now() - self.last_update < timedelta(hours=1):
                return self.openaq_cache
        
        print("[NET] Fetching OpenAQ data for NYC...")
        
        # OpenAQ API v2 endpoint
        url = "https://api.openaq.org/v2/latest"
        
        params = {
            'limit': 100,
            'parameter': 'pm25',  # PM2.5 as proxy for emissions
            'coordinates': f"{40.7128},{-74.0060}",  # NYC center
            'radius': 50000,  # 50km radius
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            stations = []
            if 'results' in data:
                for result in data['results']:
                    if 'coordinates' in result and 'measurements' in result:
                        coord = result['coordinates']
                        for measurement in result['measurements']:
                            if measurement['parameter'] == 'pm25':
                                stations.append({
                                    'lat': coord['latitude'],
                                    'lon': coord['longitude'],
                                    'value': measurement['value'],
                                    'unit': measurement['unit'],
                                    'location': result.get('location', 'Unknown')
                                })
            
            self.openaq_cache = stations
            print(f"[OK] Fetched {len(stations)} OpenAQ measurements")
            return stations
            
        except Exception as e:
            print(f"[ERROR] OpenAQ fetch failed: {e}")
            return []
    
    def _blend_openaq_data(self, grid: np.ndarray, lats: np.ndarray, 
                           lons: np.ndarray, openaq_data: List[Dict]) -> np.ndarray:
        """
        Blend real OpenAQ measurements into the synthetic grid
        """
        if not openaq_data:
            return grid
        
        print(f"[LINK] Blending {len(openaq_data)} OpenAQ measurements into grid...")
        
        for station in openaq_data:
            lat = station['lat']
            lon = station['lon']
            pm25_value = station['value']
            
            # Convert PM2.5 to emission proxy (simplified conversion)
            # Typical PM2.5: 5-50 Âµg/mÂ³, Emissions: 20-200 kg COâ‚‚/kmÂ²/day
            emission_proxy = pm25_value * 2.5
            
            # Find nearest grid points and apply influence
            lat_idx = np.argmin(np.abs(lats - lat))
            lon_idx = np.argmin(np.abs(lons - lon))
            
            # Apply with Gaussian kernel (influence nearby cells)
            for i in range(max(0, lat_idx-2), min(len(lats), lat_idx+3)):
                for j in range(max(0, lon_idx-2), min(len(lons), lon_idx+3)):
                    distance = np.sqrt((i - lat_idx)**2 + (j - lon_idx)**2)
                    weight = np.exp(-distance**2 / 2)
                    grid[i, j] = grid[i, j] * 0.7 + emission_proxy * 0.3 * weight
        
        return grid
    
    def get_baseline_grid(self) -> List[Tuple[float, float, float]]:
        """
        Returns baseline grid as list of (lat, lon, value) tuples
        """
        if self.baseline_cache is None:
            self._generate_baseline()
        
        lats, lons, emissions = self.baseline_cache
        
        # Convert to list of points
        points = []
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                points.append((lat, lon, emissions[i, j]))
        
        return points
    
    def apply_intervention(self, intervention: Dict) -> List[Tuple[float, float, float]]:
        """
        Apply intervention to emissions grid
        
        Args:
            intervention: Dict with keys:
                - borough: str or "citywide"
                - sector: str (transport, buildings, industry)
                - reduction_percent: float
                - description: str
        """
        if self.baseline_cache is None:
            self._generate_baseline()
        
        lats, lons, baseline_emissions = self.baseline_cache
        modified_emissions = baseline_emissions.copy()
        
        borough = intervention.get('borough', 'citywide')
        reduction = intervention.get('reduction_percent', 0) / 100.0
        sector = intervention.get('sector', 'transport')
        description = intervention.get('description', '')
        
        print(f"ðŸŽ¯ Applying intervention: {reduction*100}% reduction in {sector} for {borough}")
        
        # Sector-specific reduction factors
        sector_factors = {
            'transport': 0.35,  # Transport is ~35% of urban COâ‚‚
            'buildings': 0.45,  # Buildings ~45%
            'industry': 0.20,   # Industry ~20%
            'all': 1.0
        }
        
        sector_factor = sector_factors.get(sector, 0.35)
        effective_reduction = reduction * sector_factor
        
        # Use AI-generated spatial pattern if available
        if 'spatial_pattern' in intervention:
            # Apply AI-generated spatial pattern
            ai_pattern = intervention['spatial_pattern']
            print(f"[AI] Applying {len(ai_pattern)} AI-generated spatial points")
            
            # Create dramatic spatial variations based on AI pattern
            for pattern_lat, pattern_lon, pattern_intensity in ai_pattern:
                # Apply reduction to nearby grid points with distance-based falloff
                for i, lat in enumerate(lats):
                    for j, lon in enumerate(lons):
                        # CRITICAL: Only apply to points within the target borough
                        if not self._is_in_target_area(lat, lon, borough):
                            continue
                            
                        distance = np.sqrt((lat - pattern_lat)**2 + (lon - pattern_lon)**2)
                        
                        # Create larger impact radius (0.08 degrees ≈ 8km) for more visible effects
                        if distance < 0.08:
                            # Calculate impact based on distance and intensity
                            impact_factor = pattern_intensity * (1 - distance * 12)  # Slower falloff
                            impact_factor = max(0.3, impact_factor)  # Higher minimum impact
                            
                            # Apply dramatic reduction based on AI pattern
                            reduction_factor = 1.0 - (effective_reduction * impact_factor * 3.0)  # 3x multiplier for visibility
                            modified_emissions[i, j] *= max(0.01, reduction_factor)  # Allow very deep reductions
                            
                            # Add deterministic variation based on coordinates for consistency
                            coord_hash = hash(f"{lat:.3f}_{lon:.3f}_{pattern_lat:.3f}_{pattern_lon:.3f}") % 1000
                            variation_factor = 0.7 + (coord_hash / 1000.0) * 0.6  # 0.7 to 1.3 range
                            modified_emissions[i, j] *= variation_factor
        else:
            # Fallback to old pattern generation
            intervention_pattern = self._create_ai_spatial_pattern(
                lats, lons, borough, sector, description, reduction
            )
            
            # Apply reduction with AI-generated spatial pattern
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        # Get AI-calculated spatial intensity for this point
                        spatial_intensity = intervention_pattern[i, j]
                        
                        # Apply reduction scaled by AI spatial intensity
                        reduction_factor = 1.0 - (effective_reduction * spatial_intensity)
                        modified_emissions[i, j] *= max(0.05, reduction_factor)  # Keep minimum 5%
        
        # Convert to list of points
        points = []
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                points.append((lat, lon, modified_emissions[i, j]))
        
        return points
    
    def _create_ai_spatial_pattern(self, lats: np.ndarray, lons: np.ndarray, 
                                 borough: str, sector: str, description: str, 
                                 reduction_percent: float) -> np.ndarray:
        """
        Create AI-driven spatial pattern based on intervention specifics
        Uses deterministic algorithms to create unique patterns for each prompt
        """
        pattern = np.zeros((len(lats), len(lons)))
        
        # Create unique seed based on all intervention parameters
        unique_seed = hash(f"{borough}_{sector}_{description}_{reduction_percent}") % 2**32
        np.random.seed(unique_seed)
        
        # Base pattern intensity based on reduction percentage
        base_intensity = min(reduction_percent / 100.0, 1.0)
        
        # Sector-specific spatial modeling
        if sector == 'transport':
            pattern = self._model_transport_intervention(lats, lons, borough, description, base_intensity)
        elif sector == 'buildings':
            pattern = self._model_buildings_intervention(lats, lons, borough, description, base_intensity)
        elif sector == 'industry':
            pattern = self._model_industry_intervention(lats, lons, borough, description, base_intensity)
        elif sector == 'energy':
            pattern = self._model_energy_intervention(lats, lons, borough, description, base_intensity)
        else:
            pattern = self._model_citywide_intervention(lats, lons, borough, base_intensity)
        
        return pattern
    
    def _model_transport_intervention(self, lats: np.ndarray, lons: np.ndarray, 
                                    borough: str, description: str, base_intensity: float) -> np.ndarray:
        """AI-driven transport intervention modeling"""
        pattern = np.zeros((len(lats), len(lons)))
        
        # NYC major transportation corridors
        transport_corridors = {
            'Manhattan': [
                (-73.9857, 40.7589, 2.0),  # Broadway
                (-73.9712, 40.7831, 1.8),  # 5th Ave
                (-73.9442, 40.6782, 1.6),  # Brooklyn Bridge
                (-73.9857, 40.7505, 1.9),  # Times Square
            ],
            'Brooklyn': [
                (-73.9442, 40.6782, 1.5),  # Brooklyn Bridge
                (-73.9857, 40.6782, 1.3),  # Atlantic Ave
                (-73.9857, 40.6500, 1.2),  # Flatbush Ave
            ],
            'Queens': [
                (-73.7949, 40.7282, 1.4),  # Queens Blvd
                (-73.7781, 40.6413, 1.6),  # JFK Airport
                (-73.8740, 40.7769, 1.5),  # LaGuardia Airport
            ],
            'Bronx': [
                (-73.8648, 40.8448, 1.3),  # Grand Concourse
                (-73.8648, 40.8200, 1.2),  # Major Deegan
            ],
            'Staten Island': [
                (-74.1502, 40.5795, 1.1),  # Staten Island Expressway
                (-74.1502, 40.6200, 1.0),  # Hylan Blvd
            ]
        }
        
        # Get corridors for specific borough or all if citywide
        corridors = transport_corridors.get(borough, [])
        if borough.lower() == 'citywide':
            corridors = [corridor for borough_corridors in transport_corridors.values() 
                        for corridor in borough_corridors]
        
        # Apply corridor-based patterns
        for corridor_lon, corridor_lat, intensity in corridors:
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        distance = np.sqrt((lat - corridor_lat)**2 + (lon - corridor_lon)**2)
                        if distance < 0.03:  # Within ~3km
                            corridor_effect = intensity * base_intensity * (1 - distance * 20)
                            pattern[i, j] += corridor_effect
        
        # Add description-specific variations
        if 'taxi' in description.lower() or 'cab' in description.lower():
            # Taxis concentrate in commercial areas (borough-specific)
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        # Apply taxi concentration effect within the target borough
                        pattern[i, j] *= 1.5
        elif 'bus' in description.lower():
            # Buses follow major routes
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.2
        elif 'ev' in description.lower() or 'electric' in description.lower():
            # EVs have charging station patterns
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.3
        
        # Add deterministic noise based on description
        noise_seed = hash(f"transport_{description}") % 2**32
        np.random.seed(noise_seed)
        noise = np.random.normal(0.2, 0.1, pattern.shape)
        pattern += noise
        pattern = np.clip(pattern, 0, 2)
        
        return pattern
    
    def _model_buildings_intervention(self, lats: np.ndarray, lons: np.ndarray, 
                                    borough: str, description: str, base_intensity: float) -> np.ndarray:
        """AI-driven buildings intervention modeling"""
        pattern = np.zeros((len(lats), len(lons)))
        
        # NYC building density zones
        building_zones = {
            'Manhattan': [
                (40.7580, -73.9855, 2.5),  # Times Square (highest density)
                (40.7128, -74.0060, 2.3),  # Financial District
                (40.7505, -73.9934, 2.2),  # Midtown
                (40.7831, -73.9712, 2.0),  # Upper East Side
            ],
            'Brooklyn': [
                (40.6782, -73.9442, 1.8),  # Downtown Brooklyn
                (40.6500, -73.9857, 1.6),  # Park Slope
                (40.6200, -73.9500, 1.4),  # Bay Ridge
            ],
            'Queens': [
                (40.7282, -73.7949, 1.5),  # Long Island City
                (40.7500, -73.8500, 1.3),  # Astoria
                (40.7000, -73.8000, 1.2),  # Jamaica
            ],
            'Bronx': [
                (40.8448, -73.8648, 1.4),  # South Bronx
                (40.8200, -73.9000, 1.2),  # Fordham
            ],
            'Staten Island': [
                (40.5795, -74.1502, 1.0),  # St. George
                (40.6200, -74.1000, 0.9),  # New Dorp
            ]
        }
        
        # Get zones for specific borough or all if citywide
        zones = building_zones.get(borough, [])
        if borough.lower() == 'citywide':
            zones = [zone for borough_zones in building_zones.values() 
                    for zone in borough_zones]
        
        # Apply building density patterns
        for zone_lat, zone_lon, density in zones:
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        distance = np.sqrt((lat - zone_lat)**2 + (lon - zone_lon)**2)
                        if distance < 0.04:  # Within ~4km
                            zone_effect = density * base_intensity * (1 - distance * 15)
                            pattern[i, j] += zone_effect
        
        # Add description-specific variations
        if 'solar' in description.lower() or 'panel' in description.lower():
            # Solar panels work better on south-facing roofs
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        # Higher impact in areas with more sun exposure
                        pattern[i, j] *= 1.3
        elif 'green' in description.lower() or 'roof' in description.lower():
            # Green roofs work better on flat roofs (commercial buildings)
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        # Commercial areas get more green roof impact
                        if 40.70 < lat < 40.80 and -74.02 < lon < -73.93:
                            pattern[i, j] *= 1.4
                        else:
                            pattern[i, j] *= 1.1
        elif 'insulation' in description.lower() or 'heating' in description.lower():
            # Insulation affects older buildings more
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.2
        
        # Add deterministic noise based on description
        noise_seed = hash(f"buildings_{description}") % 2**32
        np.random.seed(noise_seed)
        noise = np.random.normal(0.15, 0.08, pattern.shape)
        pattern += noise
        pattern = np.clip(pattern, 0, 2)
        
        return pattern
    
    def _model_industry_intervention(self, lats: np.ndarray, lons: np.ndarray, 
                                   borough: str, description: str, base_intensity: float) -> np.ndarray:
        """AI-driven industry intervention modeling"""
        pattern = np.zeros((len(lats), len(lons)))
        
        # NYC industrial zones
        industrial_zones = {
            'Queens': [
                (40.6413, -73.7781, 2.0),  # JFK Airport area
                (40.7769, -73.8740, 1.8),  # LaGuardia Airport area
                (40.7000, -73.8000, 1.5),  # Jamaica industrial
            ],
            'Brooklyn': [
                (40.6500, -73.9500, 1.6),  # Sunset Park industrial
                (40.6200, -73.9000, 1.4),  # Red Hook
            ],
            'Bronx': [
                (40.8200, -73.9000, 1.3),  # Hunts Point
                (40.8448, -73.8648, 1.2),  # South Bronx industrial
            ],
            'Staten Island': [
                (40.5795, -74.1502, 1.5),  # Port area
                (40.6200, -74.1000, 1.2),  # Industrial zones
            ],
            'Manhattan': [
                (40.7128, -74.0060, 1.0),  # Limited industrial in Manhattan
            ]
        }
        
        # Get zones for specific borough or all if citywide
        zones = industrial_zones.get(borough, [])
        if borough.lower() == 'citywide':
            zones = [zone for borough_zones in industrial_zones.values() 
                    for zone in borough_zones]
        
        # Apply industrial zone patterns
        for zone_lat, zone_lon, intensity in zones:
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        distance = np.sqrt((lat - zone_lat)**2 + (lon - zone_lon)**2)
                        if distance < 0.05:  # Within ~5km
                            zone_effect = intensity * base_intensity * (1 - distance * 12)
                            pattern[i, j] += zone_effect
        
        # Add description-specific variations
        if 'manufacturing' in description.lower():
            # Manufacturing concentrates in specific zones
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.3
        elif 'port' in description.lower() or 'shipping' in description.lower():
            # Port activities concentrate near water
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        if self._is_near_water(lat, lon):
                            pattern[i, j] *= 1.5
        elif 'airport' in description.lower():
            # Airport-specific interventions
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.4
        
        # Add deterministic noise based on description
        noise_seed = hash(f"industry_{description}") % 2**32
        np.random.seed(noise_seed)
        noise = np.random.normal(0.1, 0.05, pattern.shape)
        pattern += noise
        pattern = np.clip(pattern, 0, 2)
        
        return pattern
    
    def _is_near_water(self, lat: float, lon: float) -> bool:
        """Check if point is near water (simplified)"""
        # Hudson River (west of Manhattan)
        if lon < -74.02 and 40.70 < lat < 40.88:
            return True
        # East River
        if -73.98 < lon < -73.93 and 40.70 < lat < 40.80:
            return True
        # New York Harbor
        if lat < 40.62 and -74.05 < lon < -74.00:
            return True
        return False
    
    def _model_energy_intervention(self, lats: np.ndarray, lons: np.ndarray, 
                                 borough: str, description: str, base_intensity: float) -> np.ndarray:
        """AI-driven energy intervention modeling"""
        pattern = np.ones((len(lats), len(lons))) * 0.8 * base_intensity
        
        # NYC energy consumption zones
        energy_zones = {
            'Manhattan': [
                (40.7580, -73.9855, 2.2),  # Times Square (highest consumption)
                (40.7128, -74.0060, 2.0),  # Financial District
                (40.7505, -73.9934, 1.8),  # Midtown
            ],
            'Brooklyn': [
                (40.6782, -73.9442, 1.6),  # Downtown Brooklyn
                (40.6500, -73.9857, 1.4),  # Park Slope
            ],
            'Queens': [
                (40.7282, -73.7949, 1.5),  # Long Island City
                (40.7500, -73.8500, 1.3),  # Astoria
            ],
            'Bronx': [
                (40.8448, -73.8648, 1.2),  # South Bronx
            ],
            'Staten Island': [
                (40.5795, -74.1502, 1.0),  # St. George
            ]
        }
        
        # Get zones for specific borough or all if citywide
        zones = energy_zones.get(borough, [])
        if borough.lower() == 'citywide':
            zones = [zone for borough_zones in energy_zones.values() 
                    for zone in borough_zones]
        
        # Apply energy consumption patterns
        for zone_lat, zone_lon, consumption in zones:
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        distance = np.sqrt((lat - zone_lat)**2 + (lon - zone_lon)**2)
                        if distance < 0.03:  # Within ~3km
                            zone_effect = consumption * base_intensity * (1 - distance * 20)
                            pattern[i, j] += zone_effect
        
        # Add description-specific variations
        if 'solar' in description.lower() or 'renewable' in description.lower():
            # Solar/renewable energy has different distribution patterns
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.2
        elif 'grid' in description.lower() or 'power' in description.lower():
            # Grid improvements affect transmission areas
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    if self._is_in_target_area(lat, lon, borough):
                        pattern[i, j] *= 1.1
        
        # Add deterministic noise based on description
        noise_seed = hash(f"energy_{description}") % 2**32
        np.random.seed(noise_seed)
        noise = np.random.normal(0.1, 0.05, pattern.shape)
        pattern += noise
        pattern = np.clip(pattern, 0, 2)
        
        return pattern
    
    def _model_citywide_intervention(self, lats: np.ndarray, lons: np.ndarray, 
                                   borough: str, base_intensity: float) -> np.ndarray:
        """AI-driven citywide intervention modeling"""
        pattern = np.ones((len(lats), len(lons))) * base_intensity
        
        # Citywide interventions have higher impact in denser areas
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                if self._is_in_target_area(lat, lon, borough):
                    # Manhattan gets higher impact
                    if borough.lower() == 'manhattan':
                        pattern[i, j] *= 1.3
                    elif borough.lower() == 'brooklyn':
                        pattern[i, j] *= 1.1
                    else:
                        pattern[i, j] *= 1.0
        
        return pattern
    
    def _add_ai_variation(self, emissions: np.ndarray, sector: str, 
                         borough: str, description: str, reduction_percent: float) -> np.ndarray:
        """Add AI-driven variation based on intervention specifics"""
        # Create unique variation based on all parameters
        variation_seed = hash(f"{sector}_{borough}_{description}_{reduction_percent}") % 2**32
        np.random.seed(variation_seed)
        
        # Different variation patterns by sector
        if sector == 'transport':
            # Transport has more linear variation (along roads)
            variation = np.random.normal(0, 0.08, emissions.shape)
        elif sector == 'buildings':
            # Buildings have more uniform variation
            variation = np.random.normal(0, 0.05, emissions.shape)
        elif sector == 'industry':
            # Industry has concentrated variation
            variation = np.random.normal(0, 0.12, emissions.shape)
        elif sector == 'energy':
            # Energy has grid-based variation
            variation = np.random.normal(0, 0.06, emissions.shape)
        else:
            variation = np.random.normal(0, 0.07, emissions.shape)
        
        # Apply variation
        emissions = emissions * (1 + variation)
        emissions = np.maximum(emissions, 0.05)  # Keep minimum emissions
        
        return emissions
    
    def _is_in_target_area(self, lat: float, lon: float, target: str) -> bool:
        """
        Check if point is in target borough using precise boundaries
        """
        if target.lower() == 'citywide' or target.lower() == 'all':
            return True
        
        # Define precise borough boundaries
        borough_bounds = {
            'Manhattan': (40.70, 40.80, -74.02, -73.93),
            'Brooklyn': (40.57, 40.70, -74.05, -73.82),
            'Queens': (40.54, 40.80, -74.05, -73.70),
            'Bronx': (40.78, 40.92, -73.95, -73.77),
            'Staten Island': (40.49, 40.65, -74.26, -74.05)
        }
        
        if target in borough_bounds:
            min_lat, max_lat, min_lon, max_lon = borough_bounds[target]
            return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
        
        return True  # Default: apply citywide
    
    def get_last_update_time(self) -> str:
        """Returns timestamp of last data update"""
        if self.last_update:
            return self.last_update.isoformat()
        return datetime.now().isoformat()


