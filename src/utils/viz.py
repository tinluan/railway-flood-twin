import matplotlib.pyplot as plt
import seaborn as sns

def set_academic_style():
    """Sets a consistent, IEEE/ASCE style for scientific plots."""
    sns.set_context("paper", font_scale=1.5)
    sns.set_style("whitegrid")
    
    # Professional academic colors (De-saturated to look good in B&W too)
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['#003366', '#D95319', '#EDB120', '#7E2F8E'])
    
    # Modern Typography
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    
    # Line and Marker Styles
    plt.rcParams['lines.linewidth'] = 2.0
    plt.rcParams['lines.markersize'] = 8

def save_for_report(fig, name):
    """Saves a figure to the report/figures directory with high DPI."""
    from src.utils.paths import paths
    dest = paths.REPORT_FIGURES / f"{name}.png"
    fig.savefig(dest, dpi=300, bbox_inches='tight')
    print(f"[INFO] Scientific figure saved to: {dest}")
