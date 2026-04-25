import os
import pandas as pd
import geopandas as gpd
import sys

# Import our central path manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import STAGING_DATA, PROCESSED_DATA

class MirrorDBProcessor:
    """Merges BIM and GIS data to create the Handoff Schema for HEC-RAS."""
    
    def __init__(self):
        self.crs = "EPSG:2154" # Lambert 93

    def generate_mirror_db(self):
        """
        Intersects BIM (ballast height) with GIS (terrain height).
        Implements the 'Funnel' hotspot strategy.
        """
        print("Generating Mirror Database (Handoff Schema)...")
        
        # 1. Load staging data (Mocking the merge for the demo)
        # In real usage, this would use gpd.overlay()
        data = {
            "segment_id": [f"SEG_{i:03}" for i in range(1, 11)],
            "lat": [45.75 + (i * 0.001) for i in range(1, 11)],
            "lon": [4.85 + (i * 0.001) for i in range(1, 11)],
            "z_terrain": [220.5, 221.0, 224.2, 219.8, 218.5, 222.1, 223.5, 220.2, 219.0, 221.5],
            "z_ballast": [221.5, 222.0, 225.2, 220.8, 219.5, 223.1, 224.5, 221.2, 220.0, 222.5],
            "is_hotspot": [False, False, True, True, True, False, False, True, False, False]
        }
        
        df = pd.DataFrame(data)
        
        # Filter for Hotspots (The Funnel Strategy)
        hotspots = df[df['is_hotspot'] == True]
        
        output_path = PROCESSED_DATA / "handoff_segments.csv"
        df.to_csv(output_path, index=False)
        
        print(f"Mirror DB created with {len(hotspots)} active hotspots.")
        return hotspots

if __name__ == "__main__":
    processor = MirrorDBProcessor()
    processor.generate_mirror_db()
