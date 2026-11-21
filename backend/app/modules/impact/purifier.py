from typing import Dict, Any
import math

class PurifierModel:
    def __init__(self):
        self.ach_natural_closed = 0.5
        self.ach_natural_open = 2.0
        self.penetration_closed = 0.7
        self.penetration_open = 1.0
        self.deposition_k = 0.2

    def calculate_steady_state(self, ambient_pm25: float, floor_area_sqm: float = 20.0, cadr_m3h: float = 250.0, ceiling_height_m: float = 2.7, windows_open: bool = False) -> Dict[str, Any]:
        v_m3 = max(1.0, floor_area_sqm * ceiling_height_m)
        ach_nat = self.ach_natural_open if windows_open else self.ach_natural_closed
        p = self.penetration_open if windows_open else self.penetration_closed
        k_dep = self.deposition_k

        ach_pur = cadr_m3h / v_m3
        lambda_tot = ach_nat + ach_pur + k_dep
        c_ss = (p * ach_nat * ambient_pm25) / lambda_tot

        lambda_base = ach_nat + k_dep
        c_base = (p * ach_nat * ambient_pm25) / lambda_base
        reduction_pct = max(0.0, (1.0 - (c_ss / max(1.0, c_base))) * 100.0)

        target = 35.0
        time_to_target_min = None
        if c_base > target > c_ss:
            t_hours = -math.log((target - c_ss) / (c_base - c_ss)) / lambda_tot
            time_to_target_min = round(t_hours * 60, 0)

        return {
            "formula_id": "IMP-PURIFIER-01",
            "value": round(c_ss, 1),
            "unit": "µg/m³ steady-state indoor PM2.5",
            "before": round(c_base, 1),
            "after": round(c_ss, 1),
            "reduction_pct": round(reduction_pct, 1),
            "confidence": "Medium",
            "time_to_target_35_min": time_to_target_min,
            "assumptions": [
                f"Room volume {round(v_m3, 1)} m³ with CADR {cadr_m3h} m³/h",
                f"Natural ACH {ach_nat} 1/h with penetration factor {p}",
                f"Deposition rate {k_dep} 1/h"
            ]
        }

purifier_model = PurifierModel()
