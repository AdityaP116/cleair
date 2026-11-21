from typing import Dict, Any

class ExposureCalculator:
    def __init__(self):
        self.inhalation_rates = {
            "adult": {"rest": 0.5, "light": 1.0, "exercise": 2.0},
            "child": {"rest": 0.3, "light": 0.6, "exercise": 1.2}
        }
        self.cigarette_divisor = 22.0
        self.cigarette_disclaimer = "Rough comparison for intuition only. It is not a medical measurement."

    def calculate_dose(self, concentration_ugm3: float, hours: float, is_child: bool = False, activity: str = "light") -> float:
        rate = self.inhalation_rates["child" if is_child else "adult"].get(activity, 1.0)
        return round(concentration_ugm3 * hours * rate, 2)

    def calculate_cigarette_equiv(self, pm25_24h_avg: float, exposure_hours: float = 24.0) -> Dict[str, Any]:
        daily_equiv = pm25_24h_avg / self.cigarette_divisor
        scaled_equiv = daily_equiv * (exposure_hours / 24.0)
        return {
            "formula_id": "IMP-CIG-01",
            "value": round(scaled_equiv, 2),
            "unit": "cigarettes/day equivalent",
            "disclaimer": self.cigarette_disclaimer,
            "assumptions": [
                "Heuristic: 22 µg/m³ 24h PM2.5 average approximates particulate mass of 1 cigarette",
                self.cigarette_disclaimer
            ]
        }

exposure_calc = ExposureCalculator()
