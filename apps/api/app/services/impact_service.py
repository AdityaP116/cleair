"""
Impact Calculator Service (SRS B9)
Pure, deterministic functions with full test coverage and formula IDs.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import math
import yaml

IMPACT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "impact.yaml"

class ImpactCalculator:
    def __init__(self, config_path: Path = IMPACT_CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.inhalation_rates = self.config["inhalation_rates"]
        self.mask_reduction = self.config["mask_reduction"]
        self.indoor_model = self.config["indoor_model"]
        self.cigarette_config = self.config["cigarette_equivalence"]
        self.commute_factors = self.config["commute_emission_factors"]

    def calc_mask_impact(self, ambient_pm25: float, mask_type: str = "n95_good", duration_hours: float = 1.0, is_child: bool = False) -> Dict[str, Any]:
        """Formula: IMP-MASK-01"""
        eff = self.mask_reduction.get(mask_type, 0.75)
        after_pm25 = ambient_pm25 * (1.0 - eff)
        
        ir = self.inhalation_rates["child"]["light"] if is_child else self.inhalation_rates["adult"]["light"]
        inhaled_before = ambient_pm25 * duration_hours * ir
        inhaled_after = after_pm25 * duration_hours * ir
        saved_dose = inhaled_before - inhaled_after

        return {
            "formula_id": "IMP-MASK-01",
            "value": round(saved_dose, 2),
            "unit": "µg PM2.5 inhaled avoided",
            "before": round(ambient_pm25, 1),
            "after": round(after_pm25, 1),
            "reduction_pct": round(eff * 100, 1),
            "confidence": "Medium",
            "assumptions": [
                f"Effective real-world filtration reduction {int(eff * 100)}% for {mask_type}",
                f"Inhalation rate {ir} m³/h for {'child' if is_child else 'adult'} light activity"
            ]
        }

    def calc_purifier_impact(self, ambient_pm25: float, floor_area_sqm: float = 20.0, cadr_m3h: float = 250.0, ceiling_height_m: float = 2.7, windows_open: bool = False) -> Dict[str, Any]:
        """Formula: IMP-PURIFIER-01 (Single-zone mass balance model)"""
        v_m3 = max(1.0, floor_area_sqm * ceiling_height_m)
        ach_nat = self.indoor_model["ach_natural_open"] if windows_open else self.indoor_model["ach_natural_closed"]
        p = self.indoor_model["penetration_open"] if windows_open else self.indoor_model["penetration_closed"]
        k_dep = self.indoor_model["deposition_rate_k"]
        
        ach_pur = cadr_m3h / v_m3
        lambda_tot = ach_nat + ach_pur + k_dep
        c_ss = (p * ach_nat * ambient_pm25) / lambda_tot

        # Baseline without purifier
        lambda_base = ach_nat + k_dep
        c_base = (p * ach_nat * ambient_pm25) / lambda_base
        
        reduction = max(0.0, (1.0 - (c_ss / max(1.0, c_base))) * 100.0)

        # Time to reach target 35 ug/m3 from baseline
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
            "reduction_pct": round(reduction, 1),
            "confidence": "Medium",
            "time_to_target_35_min": time_to_target_min,
            "assumptions": [
                f"Room volume {round(v_m3, 1)} m³ with CADR {cadr_m3h} m³/h",
                f"Natural ACH {ach_nat} 1/h with penetration factor {p}",
                f"Deposition rate {k_dep} 1/h"
            ]
        }

    def calc_cigarette_equivalence(self, pm25_24h_avg: float, exposure_hours: float = 24.0) -> Dict[str, Any]:
        """Formula: IMP-CIG-01 (Berkeley Earth heuristic)"""
        divisor = self.cigarette_config["ugm3_per_cigarette"]
        daily_equiv = pm25_24h_avg / divisor
        scaled_equiv = daily_equiv * (exposure_hours / 24.0)
        
        return {
            "formula_id": "IMP-CIG-01",
            "value": round(scaled_equiv, 2),
            "unit": "cigarettes/day equivalent",
            "before": None,
            "after": None,
            "reduction_pct": None,
            "confidence": "Low",
            "disclaimer": self.cigarette_config["disclaimer"],
            "assumptions": [
                "Heuristic: 22 µg/m³ 24h PM2.5 average approximates the particulate dose of 1 cigarette",
                self.cigarette_config["disclaimer"]
            ]
        }

    def calc_commute_switch(self, distance_km: float, baseline_mode: str = "petrol_car", new_mode: str = "metro", round_trips: int = 1) -> Dict[str, Any]:
        """Formula: IMP-COMMUTE-01"""
        ef_base = self.commute_factors.get(baseline_mode, 0.17)
        ef_new = self.commute_factors.get(new_mode, 0.03)
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
                f"Emission factor {ef_base} kg CO₂/km ({baseline_mode}) vs {ef_new} kg CO₂/km ({new_mode})",
                f"Total distance {total_km} km"
            ]
        }

    def calc_clean_air_score(self, exposure_reduction_pct: float, action_consistency_pct: float, emissions_saved_kg: float) -> int:
        """Formula: FR-DSH-02 (0 to 100 clean air score)"""
        part1 = min(40.0, (exposure_reduction_pct / 100.0) * 40.0)
        part2 = min(30.0, (action_consistency_pct / 100.0) * 30.0)
        part3 = min(30.0, (emissions_saved_kg / 5.0) * 30.0) # 5 kg CO2/week gives max score
        return int(max(0, min(100, round(part1 + part2 + part3))))
