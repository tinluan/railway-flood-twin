import numpy as np
from scipy.stats import norm

class FragilityEvaluator:
    """Calculates Probability of Failure based on water depth and velocity."""
    
    def __init__(self):
        # Parameters for Ballast Scour Fragility (Log-normal distribution)
        # Median threshold (m) and Standard Deviation
        self.median_depth = 0.3  # 30cm depth is critical for ballast
        self.sigma = 0.4

    def calculate_p_failure(self, water_depth_m):
        """
        Calculates the probability of ballast failure (0.0 to 1.0).
        """
        if water_depth_m <= 0:
            return 0.0
            
        # Log-normal CDF
        p = norm.cdf(np.log(water_depth_m / self.median_depth) / self.sigma)
        return round(float(p), 3)

    def get_risk_category(self, p_failure):
        """Maps probability to RAMS risk classes."""
        if p_failure < 0.20:
            return "LOW"
        elif 0.20 <= p_failure <= 0.50:
            return "MEDIUM"
        else:
            return "HIGH"

if __name__ == "__main__":
    evaluator = FragilityEvaluator()
    test_depths = [0.05, 0.15, 0.35, 0.60]
    
    print("Fragility Curve Test:")
    for d in test_depths:
        p = evaluator.calculate_p_failure(d)
        cat = evaluator.get_risk_category(p)
        print(f"Depth: {d}m | P(Failure): {p*100}% | Category: {cat}")
