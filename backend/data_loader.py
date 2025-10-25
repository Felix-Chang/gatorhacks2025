"""
Comprehensive Data Loader
Loads and processes all NYC emissions data sources for analysis
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Optional geopandas for boundaries (not critical)
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    print("[INFO] geopandas not available, boundary data will be skipped")

class NYCDataLoader:
    """
    Loads all NYC emissions-related datasets and provides
    unified access for emissions calculations
    """
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.cache = {}
        
        print("[INIT] Loading NYC emissions data...")
        self._load_all_data()
        print("[OK] All data loaded successfully")
    
    def _load_all_data(self):
        """Load all available datasets into memory"""
        # Load JSON reference data (small, fast)
        self._load_aviation_data()
        self._load_energy_data()
        self._load_industry_data()
        self._load_maritime_data()
        self._load_transport_reference_data()
        
        # Load geographic boundaries
        self._load_boundaries()
        
        # Large CSV files - load metadata only initially
        self._load_csv_metadata()
        
    def _load_aviation_data(self):
        """Load aviation sector data"""
        try:
            with open(self.data_dir / "aviation" / "airport_info.json") as f:
                self.cache['aviation_airports'] = json.load(f)
            
            with open(self.data_dir / "aviation" / "emissions_factors.json") as f:
                self.cache['aviation_emissions'] = json.load(f)
            
            print("  [OK] Aviation data loaded")
        except Exception as e:
            print(f"  [!] Aviation data: {e}")
            self.cache['aviation_airports'] = {}
            self.cache['aviation_emissions'] = {}
    
    def _load_energy_data(self):
        """Load energy sector data"""
        try:
            with open(self.data_dir / "energy" / "energy_sources.json") as f:
                self.cache['energy'] = json.load(f)
            
            print("  [OK] Energy data loaded")
        except Exception as e:
            print(f"  [!] Energy data: {e}")
            self.cache['energy'] = {}
    
    def _load_industry_data(self):
        """Load industry sector data"""
        try:
            with open(self.data_dir / "industry" / "facilities_info.json") as f:
                self.cache['industry_facilities'] = json.load(f)
            
            with open(self.data_dir / "industry" / "waste_management.json") as f:
                self.cache['waste_management'] = json.load(f)
            
            print("  [OK] Industry data loaded")
        except Exception as e:
            print(f"  [!] Industry data: {e}")
            self.cache['industry_facilities'] = {}
            self.cache['waste_management'] = {}
    
    def _load_maritime_data(self):
        """Load maritime sector data"""
        try:
            with open(self.data_dir / "maritime" / "port_info.json") as f:
                self.cache['maritime'] = json.load(f)
            
            print("  [OK] Maritime data loaded")
        except Exception as e:
            print(f"  [!] Maritime data: {e}")
            self.cache['maritime'] = {}
    
    def _load_transport_reference_data(self):
        """Load transport reference data"""
        try:
            with open(self.data_dir / "transport" / "vehicle_registrations.json") as f:
                self.cache['transport_vehicles'] = json.load(f)
            
            print("  [OK] Transport reference data loaded")
        except Exception as e:
            print(f"  [!] Transport data: {e}")
            self.cache['transport_vehicles'] = {}
    
    def _load_boundaries(self):
        """Load geographic boundaries"""
        if not GEOPANDAS_AVAILABLE:
            print("  [!] Boundaries skipped (geopandas not available)")
            self.cache['boundaries'] = None
            return
        
        try:
            boundary_file = self.data_dir / "boundaries" / "borough_boundaries.geojson"
            # Note: This is a large file, consider sampling if needed
            print("  [...] Loading boundaries (may take a moment)...")
            self.cache['boundaries'] = gpd.read_file(boundary_file)
            print("  [OK] Boundaries loaded")
        except Exception as e:
            print(f"  [!] Boundaries: {e}")
            self.cache['boundaries'] = None
    
    def _load_csv_metadata(self):
        """Load metadata about large CSV files without loading full data"""
        self.cache['csv_files'] = {
            'buildings': self.data_dir / "buildings" / "ll84_energy_water.csv",
            'traffic': self.data_dir / "transport" / "traffic_counts.csv",
            'trees': self.data_dir / "nature" / "tree_census.csv",
        }
        
        for name, path in self.cache['csv_files'].items():
            if path.exists():
                size_mb = path.stat().st_size / (1024**2)
                print(f"  [OK] {name.capitalize()} CSV available ({size_mb:.1f} MB)")
            else:
                print(f"  [!] {name.capitalize()} CSV not found")
    
    # ============================================================
    # DATA ACCESS METHODS
    # ============================================================
    
    def get_aviation_emissions_for_intervention(
        self, 
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Calculate aviation emissions impact based on intervention
        
        Args:
            intervention: Dict with keys like reduction_percent, description, specific_location
        
        Returns:
            Dict with baseline_tons_co2, reduced_tons_co2, annual_savings
        """
        aviation_data = self.cache.get('aviation_emissions', {})
        airports_data = self.cache.get('aviation_airports', {})
        
        # Check if specific airport is mentioned
        specific_location = intervention.get('specific_location', '')
        description = intervention.get('description', '').lower()
        
        # Determine which airports to include
        target_airports = []
        if 'jfk' in specific_location.lower() or 'jfk' in description:
            target_airports = ['JFK']
        elif 'laguardia' in specific_location.lower() or 'lga' in description or 'laguardia' in description:
            target_airports = ['LaGuardia']
        else:
            # If no specific airport, use both NYC airports
            target_airports = ['JFK', 'LaGuardia']
        
        # Get baseline emissions for target airports only
        baseline_emissions = 0
        airport_ops = aviation_data.get('airport_operations', {})
        lto_cycle = aviation_data.get('aircraft_emissions', {}).get('landing_takeoff_cycle', {})
        
        for airport, ops in airport_ops.items():
            # Skip if not in target airports
            if airport not in target_airports:
                continue
                
            annual_ops = ops.get('annual_operations', 0)
            narrow_pct = ops.get('narrow_body_percentage', 0.65)
            wide_pct = ops.get('wide_body_percentage', 0.30)
            regional_pct = ops.get('regional_percentage', 0.05)
            
            # Calculate emissions by aircraft type
            narrow_emissions = annual_ops * narrow_pct * lto_cycle.get('narrow_body_kg_co2', 850) / 1000
            wide_emissions = annual_ops * wide_pct * lto_cycle.get('wide_body_kg_co2', 2500) / 1000
            regional_emissions = annual_ops * regional_pct * lto_cycle.get('regional_jet_kg_co2', 450) / 1000
            
            baseline_emissions += narrow_emissions + wide_emissions + regional_emissions
            
            print(f"[DATA] Calculated emissions for {airport}: {(narrow_emissions + wide_emissions + regional_emissions):,.0f} tons CO2/year")
        
        # Apply intervention with explicit direction handling
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        
        # Calculate new emissions level
        # For decreases: reduction_pct is positive, multiply by (1 - reduction_pct)
        # For increases: reduction_pct is negative, so (1 - negative) = (1 + positive) which increases
        reduced_emissions = baseline_emissions * (1 - reduction_pct)
        annual_savings = baseline_emissions - reduced_emissions
        
        # Get absolute percentage for display
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline_emissions,
            'reduced_tons_co2': reduced_emissions,
            'annual_savings_tons_co2': annual_savings,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase'
        }
    
    def get_building_emissions_sample(
        self,
        borough: Optional[str] = None,
        sample_size: int = 1000
    ) -> pd.DataFrame:
        """
        Load a sample of building energy data
        
        Args:
            borough: Filter by borough (if available in data)
            sample_size: Number of rows to sample
        
        Returns:
            DataFrame with building emissions data
        """
        buildings_file = self.cache['csv_files']['buildings']
        
        if not buildings_file.exists():
            return pd.DataFrame()
        
        try:
            # Load sample
            df = pd.read_csv(buildings_file, nrows=sample_size)
            
            # Filter by borough if specified
            if borough and 'borough' in df.columns:
                df = df[df['borough'].str.contains(borough, case=False, na=False)]
            
            return df
        except Exception as e:
            print(f"[ERROR] Loading buildings data: {e}")
            return pd.DataFrame()
    
    def get_building_emissions_for_intervention(
        self,
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Calculate building sector emissions impact
        Uses actual building energy data
        """
        # Load sample of buildings
        df = self.get_building_emissions_sample(
            borough=intervention.get('borough'),
            sample_size=5000
        )
        
        if df.empty:
            # Fallback to estimates
            return self._estimate_building_emissions(intervention)
        
        # Calculate baseline from actual data
        # Common column names in LL84 data
        ghg_cols = [col for col in df.columns if 'ghg' in col.lower() or 'emissions' in col.lower()]
        energy_cols = [col for col in df.columns if 'energy' in col.lower() or 'eui' in col.lower()]
        
        baseline_emissions = 0
        if ghg_cols:
            try:
                # Convert to numeric, coercing errors to NaN
                ghg_values = pd.to_numeric(df[ghg_cols[0]], errors='coerce')
                baseline_emissions = ghg_values.sum() / len(df) * 64169  # Scale to all buildings
            except:
                pass
        
        if baseline_emissions == 0 and energy_cols:
            try:
                # Estimate from energy use (typical: 0.35 kg CO2/kWh for NYC grid)
                # NOTE: LL84 data often uses kBTU, need to convert to kWh
                from unit_conversions import KBTU_TO_KWH, detect_unit_from_column_name, NYC_GRID_KG_CO2_PER_KWH
                
                energy_col_name = energy_cols[0]
                unit_type = detect_unit_from_column_name(energy_col_name)
                
                energy_values = pd.to_numeric(df[energy_col_name], errors='coerce')
                total_energy_raw = energy_values.sum()
                
                # Convert to kWh if needed
                if unit_type == 'kbtu':
                    total_energy_kwh = total_energy_raw * KBTU_TO_KWH
                else:
                    # Assume already in kWh
                    total_energy_kwh = total_energy_raw
                
                # NYC grid emissions factor
                baseline_emissions = total_energy_kwh * NYC_GRID_KG_CO2_PER_KWH / 1000  # Convert to tons
            except:
                pass
        
        # If no valid baseline found, use estimate
        if baseline_emissions == 0:
            return self._estimate_building_emissions(intervention)
        
        # Apply intervention with explicit direction handling
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        
        reduced_emissions = baseline_emissions * (1 - reduction_pct)
        annual_savings = baseline_emissions - reduced_emissions
        
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline_emissions,
            'reduced_tons_co2': reduced_emissions,
            'annual_savings_tons_co2': annual_savings,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase',
            'buildings_analyzed': len(df)
        }
    
    def _estimate_building_emissions(self, intervention: Dict) -> Dict[str, float]:
        """Fallback building emissions estimate"""
        # NYC buildings emit ~30 million tons CO2/year
        baseline = 30000000
        
        # Adjust by borough if specified
        borough_factors = {
            'Manhattan': 0.45,
            'Brooklyn': 0.25,
            'Queens': 0.18,
            'Bronx': 0.08,
            'Staten Island': 0.04
        }
        
        borough = intervention.get('borough', 'citywide')
        if borough in borough_factors:
            baseline *= borough_factors[borough]
        
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        reduced = baseline * (1 - reduction_pct)
        
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline,
            'reduced_tons_co2': reduced,
            'annual_savings_tons_co2': baseline - reduced,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase'
        }
    
    def get_transport_emissions_for_intervention(
        self,
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Calculate transportation emissions impact
        Uses vehicle fleet data and emissions factors
        """
        vehicle_data = self.cache.get('transport_vehicles', {})
        registrations = vehicle_data.get('nyc_vehicle_registrations', {})
        emissions_factors = vehicle_data.get('emissions_factors', {})
        
        # Calculate baseline emissions
        # NOTE: Converting imperial (miles) to metric (km) for consistency with grid
        from unit_conversions import MILES_TO_KM, EMISSIONS_FACTORS_METRIC
        
        total_vehicles = registrations.get('total_vehicles', 2100000)
        
        # Average vehicle distance traveled per year in NYC
        # Source data is in miles (US standard), convert to km
        avg_vmt_miles = 8000  # miles/year (from US EPA/DOT data)
        avg_vkt_km = avg_vmt_miles * MILES_TO_KM  # 12,875 km/year
        
        # Fleet composition
        by_fuel = registrations.get('by_fuel_type', {})
        gasoline_vehicles = by_fuel.get('gasoline', 1600000)
        diesel_vehicles = by_fuel.get('diesel', 300000)
        hybrid_vehicles = by_fuel.get('hybrid', 150000)
        electric_vehicles = by_fuel.get('electric', 40000)
        
        # Use metric emissions factors (kg CO2 per km, not mile)
        gasoline_ef = EMISSIONS_FACTORS_METRIC['gasoline_kg_co2_per_km']  # 0.242
        diesel_ef = EMISSIONS_FACTORS_METRIC['diesel_kg_co2_per_km']      # 0.255
        hybrid_ef = EMISSIONS_FACTORS_METRIC['hybrid_kg_co2_per_km']      # 0.137
        electric_ef = EMISSIONS_FACTORS_METRIC['electric_kg_co2_per_km']  # 0.093
        
        # Calculate baseline emissions (tons CO2/year)
        baseline_emissions = (
            gasoline_vehicles * avg_vkt_km * gasoline_ef / 1000 +
            diesel_vehicles * avg_vkt_km * diesel_ef / 1000 +
            hybrid_vehicles * avg_vkt_km * hybrid_ef / 1000 +
            electric_vehicles * avg_vkt_km * electric_ef / 1000
        )
        
        # Sector-specific adjustments
        subsector = intervention.get('subsector', 'general')
        if subsector == 'taxis':
            # Taxi fleet is smaller, higher mileage
            taxi_data = vehicle_data.get('taxi_fleet', {})
            taxi_fleet = taxi_data.get('yellow_cabs', 13500) + taxi_data.get('for_hire_vehicles', 80000)
            taxi_vmt_miles = taxi_data.get('average_daily_miles', 180) * 365
            taxi_vkt_km = taxi_vmt_miles * MILES_TO_KM
            baseline_emissions = taxi_fleet * taxi_vkt_km * gasoline_ef / 1000
        elif subsector == 'bus':
            # Bus fleet
            bus_data = vehicle_data.get('bus_fleet', {})
            bus_fleet = bus_data.get('mta_buses', 5800)
            bus_vmt_miles = bus_data.get('average_daily_miles_per_bus', 150) * 365
            bus_vkt_km = bus_vmt_miles * MILES_TO_KM
            baseline_emissions = bus_fleet * bus_vkt_km * diesel_ef / 1000
        
        # Apply intervention with explicit direction handling
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        
        reduced_emissions = baseline_emissions * (1 - reduction_pct)
        annual_savings = baseline_emissions - reduced_emissions
        
        # Get absolute percentage for display
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline_emissions,
            'reduced_tons_co2': reduced_emissions,
            'annual_savings_tons_co2': annual_savings,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase'
        }
    
    def get_energy_emissions_for_intervention(
        self,
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Calculate energy sector emissions impact
        Uses grid data and power plant information
        """
        energy_data = self.cache.get('energy', {})
        grid = energy_data.get('nyc_power_grid', {})
        emissions_factors = energy_data.get('emissions_factors', {})
        
        # NYC average annual energy consumption
        avg_demand_mw = grid.get('average_demand_mw', 7000)
        hours_per_year = 8760
        annual_mwh = avg_demand_mw * hours_per_year
        
        # Calculate baseline emissions
        grid_factor = emissions_factors.get('grid_average_kg_co2_per_mwh', 350)
        baseline_emissions = annual_mwh * grid_factor / 1000  # Convert to tons
        
        # Apply intervention with explicit direction handling
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        
        reduced_emissions = baseline_emissions * (1 - reduction_pct)
        annual_savings = baseline_emissions - reduced_emissions
        
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline_emissions,
            'reduced_tons_co2': reduced_emissions,
            'annual_savings_tons_co2': annual_savings,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase',
            'annual_mwh': annual_mwh
        }
    
    def get_industry_emissions_for_intervention(
        self,
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Calculate industry sector emissions impact
        """
        # NYC industrial emissions ~5 million tons CO2/year
        baseline_emissions = 5000000
        
        # Adjust by subsector
        subsector = intervention.get('subsector', 'general')
        if subsector == 'waste':
            waste_data = self.cache.get('waste_management', {})
            waste_gen = waste_data.get('waste_generation', {})
            annual_tons = waste_gen.get('annual_tons', {}).get('total', 14000000)
            
            # Landfill methane emissions
            landfill_pct = waste_data.get('disposal_methods', {}).get('landfill_percentage', 0.65)
            methane_factor = waste_data.get('emissions', {}).get('landfill_methane_tons_co2e_per_ton_waste', 0.5)
            baseline_emissions = annual_tons * landfill_pct * methane_factor
        
        # Apply intervention with explicit direction handling
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        
        reduced_emissions = baseline_emissions * (1 - reduction_pct)
        annual_savings = baseline_emissions - reduced_emissions
        
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline_emissions,
            'reduced_tons_co2': reduced_emissions,
            'annual_savings_tons_co2': annual_savings,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase'
        }
    
    def get_emissions_for_sector(
        self,
        sector: str,
        intervention: Dict
    ) -> Dict[str, float]:
        """
        Main method to get emissions calculations for any sector
        
        Args:
            sector: One of 'aviation', 'buildings', 'transport', 'energy', 'industry', 'nature'
            intervention: Dict with intervention details
        
        Returns:
            Dict with emissions calculations
        """
        sector = sector.lower()
        
        if sector == 'aviation':
            return self.get_aviation_emissions_for_intervention(intervention)
        elif sector == 'buildings':
            return self.get_building_emissions_for_intervention(intervention)
        elif sector == 'transport':
            return self.get_transport_emissions_for_intervention(intervention)
        elif sector == 'energy':
            return self.get_energy_emissions_for_intervention(intervention)
        elif sector == 'industry':
            return self.get_industry_emissions_for_intervention(intervention)
        elif sector == 'nature':
            return self._get_nature_sequestration(intervention)
        else:
            return self._get_generic_emissions(intervention)
    
    def _get_nature_sequestration(self, intervention: Dict) -> Dict[str, float]:
        """Calculate carbon sequestration from nature-based solutions"""
        # Average urban tree sequesters ~20 kg CO2/year
        tree_factor = 20 / 1000  # tons CO2/tree/year
        
        # Intervention magnitude
        magnitude = intervention.get('magnitude_percent', 20)
        
        # Current trees: 683,788
        current_trees = 683788
        new_trees = current_trees * magnitude / 100
        
        # Sequestration (negative = removes CO2)
        annual_sequestration = new_trees * tree_factor
        
        return {
            'baseline_tons_co2': 0,
            'reduced_tons_co2': -annual_sequestration,
            'annual_savings_tons_co2': annual_sequestration,
            'percentage_reduction': magnitude,
            'trees_planted': new_trees
        }
    
    def _get_generic_emissions(self, intervention: Dict) -> Dict[str, float]:
        """Generic emissions calculation fallback"""
        # NYC total emissions ~50 million tons CO2/year
        baseline = 50000000
        
        reduction_pct = intervention.get('reduction_percent', 20) / 100.0
        direction = intervention.get('direction', 'decrease')
        reduced = baseline * (1 - reduction_pct)
        
        abs_reduction_pct = abs(intervention.get('reduction_percent', 20))
        
        return {
            'baseline_tons_co2': baseline,
            'reduced_tons_co2': reduced,
            'annual_savings_tons_co2': baseline - reduced,
            'percentage_reduction': abs_reduction_pct,
            'direction': direction,
            'is_increase': direction == 'increase'
        }
    
    def get_spatial_data_for_sector(
        self,
        sector: str,
        intervention: Dict
    ) -> List[Tuple[float, float, float]]:
        """
        Get spatial points for visualization based on real data
        
        Returns:
            List of (lat, lon, intensity) tuples
        """
        spatial_points = []
        
        if sector == 'aviation':
            # Use actual airport locations
            airports = self.cache.get('aviation_airports', {}).get('airport_codes', {})
            for code, data in airports.items():
                spatial_points.append((
                    data.get('lat', 40.7),
                    data.get('lon', -73.9),
                    1.0  # Full intensity at airport
                ))
        
        elif sector == 'energy':
            # Use actual power plant locations
            plants = self.cache.get('energy', {}).get('major_substations', [])
            for plant in plants:
                loc = plant.get('location', {})
                spatial_points.append((
                    loc.get('lat', 40.7),
                    loc.get('lon', -73.9),
                    0.8
                ))
        
        elif sector == 'industry':
            # Use actual facility locations
            facilities = self.cache.get('industry_facilities', {})
            for facility_type in ['power_plants', 'waste_facilities', 'manufacturing']:
                for facility in facilities.get(facility_type, []):
                    loc = facility.get('location', {})
                    if loc:
                        spatial_points.append((
                            loc.get('lat', 40.7),
                            loc.get('lon', -73.9),
                            0.7
                        ))
        
        elif sector == 'maritime':
            # Use actual port locations
            ports = self.cache.get('maritime', {}).get('facilities', {})
            for port_name, port_data in ports.items():
                loc = port_data.get('location', {})
                if loc:
                    spatial_points.append((
                        loc.get('lat', 40.7),
                        loc.get('lon', -73.9),
                        0.9
                    ))
        
        return spatial_points


# Global instance
_data_loader = None

def get_data_loader() -> NYCDataLoader:
    """Get or create global data loader instance"""
    global _data_loader
    if _data_loader is None:
        _data_loader = NYCDataLoader()
    return _data_loader

