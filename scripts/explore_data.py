"""
Quick Data Explorer
Run this script to see summary statistics of all downloaded data
"""

import json
from pathlib import Path
import pandas as pd

data_dir = Path("data/raw")

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def explore_json(filepath):
    """Display JSON file summary"""
    with open(filepath) as f:
        data = json.load(f)
    
    print(f"\n[JSON] {filepath.name}")
    print(f"   Keys: {', '.join(list(data.keys())[:5])}")
    
    def count_items(obj, depth=0):
        if isinstance(obj, dict):
            return sum(count_items(v, depth+1) for v in obj.values())
        elif isinstance(obj, list):
            return len(obj)
        return 1
    
    total_items = count_items(data)
    print(f"   Total data points: {total_items}")

def explore_csv(filepath, max_rows=5):
    """Display CSV file summary"""
    print(f"\n[CSV] {filepath.name}")
    
    try:
        # Read just the first few rows to get info
        df = pd.read_csv(filepath, nrows=1000)
        
        print(f"   Total rows: ~{len(df):,} (sampled)")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Column names: {', '.join(df.columns[:5].tolist())}...")
        print(f"   File size: {filepath.stat().st_size / (1024**2):.1f} MB")
        
        # Show data types
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            print(f"   Numeric columns: {len(numeric_cols)}")
        
    except Exception as e:
        print(f"   Error reading file: {e}")

def explore_geojson(filepath):
    """Display GeoJSON file summary"""
    print(f"\n[GeoJSON] {filepath.name}")
    
    try:
        with open(filepath) as f:
            data = json.load(f)
        
        if 'features' in data:
            print(f"   Features: {len(data['features'])}")
            if data['features']:
                feature_type = data['features'][0].get('geometry', {}).get('type', 'Unknown')
                print(f"   Geometry type: {feature_type}")
                
                # Get properties
                props = data['features'][0].get('properties', {})
                print(f"   Properties: {', '.join(list(props.keys())[:5])}")
        
        print(f"   File size: {filepath.stat().st_size / (1024**2):.1f} MB")
        
    except Exception as e:
        print(f"   Error reading file: {e}")

def main():
    print("\n" + "="*60)
    print("     NYC EMISSIONS DATA EXPLORER")
    print("="*60)
    
    # Aviation
    print_section("AVIATION")
    for f in (data_dir / "aviation").glob("*.json"):
        explore_json(f)
    
    # Boundaries
    print_section("BOUNDARIES")
    for f in (data_dir / "boundaries").glob("*.geojson"):
        explore_geojson(f)
    
    # Buildings
    print_section("BUILDINGS")
    for f in (data_dir / "buildings").glob("*.csv"):
        explore_csv(f)
    
    # Energy
    print_section("ENERGY")
    for f in (data_dir / "energy").glob("*.json"):
        explore_json(f)
    
    # Industry
    print_section("INDUSTRY")
    for f in (data_dir / "industry").glob("*.json"):
        explore_json(f)
    
    # Maritime
    print_section("MARITIME")
    for f in (data_dir / "maritime").glob("*.json"):
        explore_json(f)
    
    # Nature
    print_section("NATURE")
    for f in (data_dir / "nature").glob("*.csv"):
        explore_csv(f)
    
    # Transport
    print_section("TRANSPORT")
    for f in (data_dir / "transport").glob("*.csv"):
        explore_csv(f)
    for f in (data_dir / "transport").glob("*.json"):
        explore_json(f)
    
    print("\n" + "="*60)
    print("  >> Data exploration complete!")
    print("  >> See DATA_SOURCES.md for detailed documentation")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

