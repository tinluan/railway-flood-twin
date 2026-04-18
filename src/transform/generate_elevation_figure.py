import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.utils.paths import paths
from src.utils.viz import set_academic_style, save_for_report

def create_elevation_distribution_plot():
    """Generates a professional academic figure showing elevation distribution by asset type."""
    print("[INFO] Generating academic elevation distribution figure...")
    
    # Load the fresh results
    df = pd.read_csv(paths.REPORT_TABLES / "Table01_Asset_Elevation_Summary.csv")
    
    # Filter out Null results (those that didn't overlap)
    df = df[df['elev_mean_m'].notnull()]
    
    # Set the style
    set_academic_style()
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Use a boxplot to show distribution and outliers
    sns.boxplot(
        data=df, 
        x='layer', 
        y='elev_mean_m', 
        ax=ax,
        palette='Blues',
        hue='layer',
        legend=False
    )
    
    # Add actual data points for more transparency (Academic best practice)
    sns.stripplot(
        data=df, 
        x='layer', 
        y='elev_mean_m', 
        color='black', 
        alpha=0.3, 
        ax=ax
    )
    
    # Final styling
    ax.set_title("Figure 01: Elevation Distribution across Railway Assets (Case Study)", pad=20)
    ax.set_xlabel("Asset Layer", labelpad=15)
    ax.set_ylabel("Mean Elevation (m above sea level)", labelpad=15)
    
    # Save to the report folder
    save_for_report(fig, "Fig01_Elevation_Distribution")
    plt.close(fig)

if __name__ == "__main__":
    try:
        create_elevation_distribution_plot()
        print("[SUCCESS] Academic figure created.")
    except Exception as e:
        print(f"[ERROR] Could not create figure: {e}")
