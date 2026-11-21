from typing import Dict, Any

class InterventionImpact:
    def __init__(self):
        self.mask_eff = {
            "n95_good": 0.75,
            "n95_poor": 0.40,
            "surgical": 0.30,
            "cloth": 0.15
        }
        self.emission_factors = {
            "petrol_car": 0.17,
            "two_wheeler": 0.04,
            "bus": 0.07,
            "metro": 0.03,
            "walk": 0.0,
            "cycle": 0.0,
            "wfh": 0.0
        }

    def calc_mask_impact(self, ambient_pm25: float, mask_type: str = "n95_good", duration_hours: float = 1.0, is_child: bool = False) -> Dict[str, Any]:
        eff = self.mask_eff.get(mask_type, 0.75)
        after_pm25 = ambient_pm25 * (1.0 - eff)
        ir = 0.6 if is_child else 1.0
        dose_saved = (ambient_pm25 - after_pm25) * duration_hours * ir

        return {
            "formula_id": "IMP-MASK-01",
            "value": round(dose_saved, 2),
            "unit": "µg PM2.5 inhaled avoided",
            "before": round(ambient_pm25, 1),
            "after": round(after_pm25, 1),
            "reduction_pct": round(eff * 100, 1),
            "confidence": "Medium",
            "assumptions": [
                f"Certified {mask_type} effective real-world filtration {int(eff*100)}%",
                f"Inhalation rate {ir} m³/h for {'child' if is_child else 'adult'} light activity"
            ]
        }

    def calc_commute_switch(self, distance_km: float, baseline_mode: str = "petrol_car", new_mode: str = "metro", round_trips: int = 1) -> Dict[str, Any]:
        ef_base = self.emission_factors.get(baseline_mode, 0.17)
        ef_new = self.emission_factors.get(new_mode, 0.03)
        total_km = distance_km * round_trips
        co2_saved = total_km * max(0.0, ef_base - ef_new)
        reduction_pct = (ef_base - ef_new) / max(0.001, ef_base) * 100

        return {
            "formula_id": "IMP-COMMUTE-01",
            "value": round(co2_saved, 2),
            "unit": "kg CO₂ saved",
            "before": round(total_km * ef_base, 2),
            "after": round(total_km * ef_new, 2),
            "reduction_pct": round(reduction_pct, 1),
            "confidence": "Medium",
            "assumptions": [
                f"ARAI emission factor {ef_base} kg CO₂/km vs {ef_new} kg CO₂/km",
                f"Round-trip distance: {total_km} km"
            ]
        }

    def calc_clean_air_score(self, exposure_reduction_pct: float, action_consistency_pct: float, emissions_saved_kg: float) -> int:
        p1 = min(40.0, (exposure_reduction_pct / 100.0) * 40.0)
        p2 = min(30.0, (action_consistency_pct / 100.0) * 30.0)
        p3 = min(30.0, (emissions_saved_kg / 5.0) * 30.0)
        return int(max(0, min(100, round(p1 + p2 + p3))))

interventions_calc = InterventionImpact()
