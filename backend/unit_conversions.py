"""
Unit Conversion Constants for NYC Emissions Data
Handles mixed imperial/metric units in source data
"""

# ==================
# LENGTH CONVERSIONS
# ==================
MILES_TO_KM = 1.609344
FEET_TO_METERS = 0.3048
METERS_TO_FEET = 3.28084
KM_TO_MILES = 0.621371

# ===============
# AREA CONVERSIONS
# ===============
SQ_FT_TO_SQ_M = 0.09290304
SQ_M_TO_SQ_FT = 10.7639
SQ_MI_TO_SQ_KM = 2.589988
SQ_KM_TO_SQ_MI = 0.386102

# ==================
# ENERGY CONVERSIONS
# ==================
BTU_TO_KWH = 0.000293071
KBTU_TO_KWH = 0.293071
KWH_TO_BTU = 3412.14
KWH_TO_KBTU = 3.41214

# ===================
# MASS CONVERSIONS
# ===================
POUNDS_TO_KG = 0.453592
KG_TO_POUNDS = 2.20462
TONS_US_TO_METRIC_TONS = 0.907185  # US short ton to metric ton

# ===========================
# EMISSIONS FACTORS (TRANSPORT)
# ===========================
# Standard EPA values (imperial)
EMISSIONS_FACTORS_IMPERIAL = {
    'gasoline_kg_co2_per_mile': 0.39,
    'diesel_kg_co2_per_mile': 0.41,
    'hybrid_kg_co2_per_mile': 0.22,
    'electric_kg_co2_per_mile': 0.15,
}

# Converted to metric
EMISSIONS_FACTORS_METRIC = {
    'gasoline_kg_co2_per_km': 0.39 / MILES_TO_KM,  # 0.242
    'diesel_kg_co2_per_km': 0.41 / MILES_TO_KM,    # 0.255
    'hybrid_kg_co2_per_km': 0.22 / MILES_TO_KM,    # 0.137
    'electric_kg_co2_per_km': 0.15 / MILES_TO_KM,  # 0.093
}

# ===========================
# NYC GRID EMISSIONS FACTOR
# ===========================
NYC_GRID_KG_CO2_PER_KWH = 0.35  # Typical NYC grid mix

def convert_vmt_to_vkt(miles):
    """Vehicle Miles Traveled to Vehicle Kilometers Traveled"""
    return miles * MILES_TO_KM

def convert_kbtu_to_kwh(kbtu):
    """Thousand BTU to Kilowatt-hours"""
    return kbtu * KBTU_TO_KWH

def convert_sq_ft_to_sq_m(sq_ft):
    """Square feet to square meters"""
    return sq_ft * SQ_FT_TO_SQ_M

def convert_emissions_per_mile_to_per_km(kg_per_mile):
    """Convert kg CO2/mile to kg CO2/km"""
    return kg_per_mile / MILES_TO_KM

# ===========================
# VALIDATION HELPERS
# ===========================
def detect_unit_from_column_name(column_name: str) -> str:
    """
    Detect units from common LL84 and NYC Open Data column names
    
    Returns: 'kbtu', 'kwh', 'sq_ft', 'sq_m', 'miles', 'km', or 'unknown'
    """
    col_lower = column_name.lower()
    
    if 'kbtu' in col_lower or 'btu' in col_lower:
        return 'kbtu'
    elif 'kwh' in col_lower or 'kilowatt' in col_lower:
        return 'kwh'
    elif 'sq_ft' in col_lower or 'sqft' in col_lower or '_ft' in col_lower:
        return 'sq_ft'
    elif 'sq_m' in col_lower or 'sqm' in col_lower or '_m2' in col_lower:
        return 'sq_m'
    elif 'mile' in col_lower or 'vmt' in col_lower:
        return 'miles'
    elif 'km' in col_lower or 'kilometer' in col_lower or 'vkt' in col_lower:
        return 'km'
    else:
        return 'unknown'

