"""
Test script to verify data integration is working properly
Tests loading data and calculating emissions for different sectors
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_data_loader():
    """Test data loader initialization and basic functionality"""
    print("\n" + "="*60)
    print("TEST 1: Data Loader Initialization")
    print("="*60)
    
    try:
        from data_loader import NYCDataLoader
        loader = NYCDataLoader()
        print("\n[OK] Data loader initialized successfully")
        return loader
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize data loader: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_aviation_calculations(loader):
    """Test aviation sector emissions calculations"""
    print("\n" + "="*60)
    print("TEST 2: Aviation Sector Calculations")
    print("="*60)
    
    intervention = {
        'sector': 'aviation',
        'reduction_percent': 25,
        'description': 'Convert 25% of flights to sustainable aviation fuel'
    }
    
    try:
        result = loader.get_emissions_for_sector('aviation', intervention)
        print(f"\n[OK] Aviation calculations successful:")
        print(f"   Baseline: {result['baseline_tons_co2']:,.0f} tons CO2/year")
        print(f"   After intervention: {result['reduced_tons_co2']:,.0f} tons CO2/year")
        print(f"   Annual savings: {result['annual_savings_tons_co2']:,.0f} tons CO2/year")
        return True
    except Exception as e:
        print(f"\n[ERROR] Aviation calculations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transport_calculations(loader):
    """Test transport sector emissions calculations"""
    print("\n" + "="*60)
    print("TEST 3: Transport Sector Calculations")
    print("="*60)
    
    intervention = {
        'sector': 'transport',
        'reduction_percent': 30,
        'subsector': 'taxis',
        'description': 'Convert 30% of taxis to EVs'
    }
    
    try:
        result = loader.get_emissions_for_sector('transport', intervention)
        print(f"\n[OK] Transport calculations successful:")
        print(f"   Baseline: {result['baseline_tons_co2']:,.0f} tons CO2/year")
        print(f"   After intervention: {result['reduced_tons_co2']:,.0f} tons CO2/year")
        print(f"   Annual savings: {result['annual_savings_tons_co2']:,.0f} tons CO2/year")
        return True
    except Exception as e:
        print(f"\n[ERROR] Transport calculations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_buildings_calculations(loader):
    """Test buildings sector emissions calculations"""
    print("\n" + "="*60)
    print("TEST 4: Buildings Sector Calculations")
    print("="*60)
    
    intervention = {
        'sector': 'buildings',
        'reduction_percent': 20,
        'borough': 'Manhattan',
        'description': 'Install solar panels on 20% of Manhattan buildings'
    }
    
    try:
        result = loader.get_emissions_for_sector('buildings', intervention)
        print(f"\n[OK] Buildings calculations successful:")
        print(f"   Baseline: {result['baseline_tons_co2']:,.0f} tons CO2/year")
        print(f"   After intervention: {result['reduced_tons_co2']:,.0f} tons CO2/year")
        print(f"   Annual savings: {result['annual_savings_tons_co2']:,.0f} tons CO2/year")
        if 'buildings_analyzed' in result:
            print(f"   Buildings analyzed: {result['buildings_analyzed']}")
        return True
    except Exception as e:
        print(f"\n[ERROR] Buildings calculations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_energy_calculations(loader):
    """Test energy sector emissions calculations"""
    print("\n" + "="*60)
    print("TEST 5: Energy Sector Calculations")
    print("="*60)
    
    intervention = {
        'sector': 'energy',
        'reduction_percent': 15,
        'description': 'Add 15% renewable energy to grid'
    }
    
    try:
        result = loader.get_emissions_for_sector('energy', intervention)
        print(f"\n[OK] Energy calculations successful:")
        print(f"   Baseline: {result['baseline_tons_co2']:,.0f} tons CO2/year")
        print(f"   After intervention: {result['reduced_tons_co2']:,.0f} tons CO2/year")
        print(f"   Annual savings: {result['annual_savings_tons_co2']:,.0f} tons CO2/year")
        if 'annual_mwh' in result:
            print(f"   Annual energy: {result['annual_mwh']:,.0f} MWh")
        return True
    except Exception as e:
        print(f"\n[ERROR] Energy calculations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spatial_data(loader):
    """Test spatial data retrieval"""
    print("\n" + "="*60)
    print("TEST 6: Spatial Data Retrieval")
    print("="*60)
    
    sectors = ['aviation', 'energy', 'industry', 'maritime']
    intervention = {'reduction_percent': 20}
    
    all_passed = True
    for sector in sectors:
        try:
            spatial_points = loader.get_spatial_data_for_sector(sector, intervention)
            if spatial_points:
                print(f"\n[OK] {sector.capitalize()}: {len(spatial_points)} spatial points")
                # Show first point as example
                if spatial_points:
                    lat, lon, intensity = spatial_points[0]
                    print(f"   Example: ({lat:.4f}, {lon:.4f}) intensity={intensity:.2f}")
            else:
                print(f"\n[WARN] {sector.capitalize()}: No spatial points (may be expected)")
        except Exception as e:
            print(f"\n[ERROR] {sector.capitalize()} spatial data failed: {e}")
            all_passed = False
    
    return all_passed

def test_data_processor_integration():
    """Test integration with data_processor"""
    print("\n" + "="*60)
    print("TEST 7: Data Processor Integration")
    print("="*60)
    
    try:
        from data_processor import NYCEmissionsData
        processor = NYCEmissionsData()
        
        # Test intervention with real data
        intervention = {
            'sector': 'transport',
            'borough': 'Manhattan',
            'reduction_percent': 25,
            'description': 'EV taxi conversion',
            'spatial_pattern': [(40.7589, -73.9857, 1.0), (40.7505, -73.9857, 0.8)]
        }
        
        result = processor.apply_intervention(intervention)
        
        if 'real_emissions' in intervention:
            print("\n[OK] Data processor integration successful!")
            print("   Real emissions data included in intervention:")
            emissions = intervention['real_emissions']
            print(f"   Baseline: {emissions['baseline_tons_co2']:,.0f} tons CO2/year")
            print(f"   Savings: {emissions['annual_savings_tons_co2']:,.0f} tons CO2/year")
        else:
            print("\n[WARN] Data processor working but no real emissions data attached")
        
        print(f"   Generated {len(result)} grid points for visualization")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Data processor integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  NYC EMISSIONS DATA INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Initialize data loader
    loader = test_data_loader()
    if not loader:
        print("\n[ERROR] Cannot continue tests without data loader")
        return
    
    # Test 2-5: Sector-specific calculations
    results.append(("Aviation", test_aviation_calculations(loader)))
    results.append(("Transport", test_transport_calculations(loader)))
    results.append(("Buildings", test_buildings_calculations(loader)))
    results.append(("Energy", test_energy_calculations(loader)))
    
    # Test 6: Spatial data
    results.append(("Spatial Data", test_spatial_data(loader)))
    
    # Test 7: Integration with data_processor
    results.append(("Data Processor Integration", test_data_processor_integration()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n>> All tests passed! Data integration is working correctly.")
    else:
        print("\n>> Some tests failed. Check errors above.")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

