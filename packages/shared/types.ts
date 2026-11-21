export type AdviceLevel = "NORMAL" | "CAUTION" | "HIGH" | "SEVERE" | "EMERGENCY";
export type ConfidenceLevel = "Low" | "Medium" | "High";

export interface SessionResponse {
  session_token: string;
  user_id: string;
}

export interface Profile {
  user_id: string;
  city?: string;
  locality?: string;
  geohash?: string;
  has_child: boolean;
  has_elderly: boolean;
  is_pregnant: boolean;
  has_respiratory_condition: boolean;
  has_heart_condition: boolean;
  commute_mode?: "walk" | "two_wheeler" | "car" | "bus" | "metro" | "train" | "wfh";
  commute_minutes_per_day?: number;
  outdoor_work: boolean;
  home_size_sqm?: number;
  ceiling_height_m?: number;
  has_purifier: boolean;
  purifier_cadr_m3h?: number;
  has_ac: boolean;
  cooking_fuel?: "lpg" | "png" | "induction" | "biomass" | "other";
  budget_tier: "free" | "low" | "mid" | "high";
  language: string;
  briefing_time: string;
}

export interface AirCurrentResponse {
  location?: { city?: string; geohash?: string };
  aqi: number;
  category: string;
  dominant_pollutant: string;
  pm25: number;
  pm10: number;
  no2?: number;
  o3?: number;
  so2?: number;
  co?: number;
  station: { name: string; distance_km: number; source: string };
  confidence: ConfidenceLevel;
  observed_at: string;
  stale: boolean;
}

export interface ForecastPoint {
  valid_at: string;
  aqi: number;
  aqi_category: string;
  pm25: number;
  pm10: number;
  wind_speed_ms?: number;
  humidity_pct?: number;
  temp_c?: number;
}

export interface AirForecastResponse {
  geohash: string;
  issued_at: string;
  points: ForecastPoint[];
}

export interface RiskResponse {
  advice_level: AdviceLevel;
  worst_aqi: number;
  worst_category: string;
  rule_id: string;
  mandatory_actions: string[];
  grap_stage?: string;
  evaluated_at: string;
}

export interface PlanBlock {
  start: string;
  end: string;
  type: string;
  note: string;
  reason?: string;
  benefit?: string;
  severity?: AdviceLevel;
}

export interface PlanResponse {
  date: string;
  best_outdoor_window?: {
    start: string;
    end: string;
    pm25: number;
    reason: string;
  };
  blocks: PlanBlock[];
}

export interface Citation {
  id: string;
  title: string;
  publisher: string;
  url: string;
  published?: string;
}

export interface ActionRecommendation {
  title: string;
  why: string;
  impact?: {
    text: string;
    value: number;
    unit: string;
    formula_id: string;
  };
  cost_tier?: "free" | "low" | "mid" | "high";
  citations?: string[];
}

export interface AgentResponse {
  advice_level: AdviceLevel;
  headline: string;
  summary: string;
  actions: ActionRecommendation[];
  plan_blocks?: PlanBlock[];
  citations: Citation[];
  uncertainty_note?: string | null;
  disclaimer: string;
  followups?: string[];
  symptom_escalation?: boolean;
  limited_mode?: boolean;
}

export interface ImpactEstimateRequest {
  action: "wear_mask" | "run_purifier" | "ventilation_timing" | "commute_switch" | "avoid_outdoor_exercise" | "cooking_ventilation";
  params?: Record<string, unknown>;
}

export interface ImpactResult {
  value: number;
  unit: string;
  before?: number | null;
  after?: number | null;
  reduction_pct?: number | null;
  assumptions: string[];
  confidence: ConfidenceLevel;
  formula_id: string;
}

export interface DashboardResponse {
  clean_air_score: number;
  streak_days: number;
  cigarette_equiv_avoided: number;
  cigarette_disclaimer: string;
  co2_saved_kg: number;
  exposure_reduction_pct?: number;
  exposure_trend: Array<{
    date: string;
    actual_ugm3h: number;
    baseline_ugm3h: number;
  }>;
  recent_actions?: Array<{
    id: string;
    action_type: string;
    logged_at: string;
    exposure_delta: number;
  }>;
}
