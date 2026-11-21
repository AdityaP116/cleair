from typing import Dict, Any, List, Optional
from datetime import datetime

class InMemoryRepository:
    def __init__(self):
        self.sessions: Dict[str, str] = {} # token -> user_id
        self.profiles: Dict[str, Dict[str, Any]] = {} # user_id -> profile dict
        self.action_logs: Dict[str, List[Dict[str, Any]]] = {} # user_id -> logs
        self.consents: Dict[str, List[Dict[str, Any]]] = {} # user_id -> consents
        
    def create_session(self, token: str, user_id: str) -> None:
        self.sessions[token] = user_id
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                "user_id": user_id,
                "city": "Delhi",
                "locality": "Anand Vihar",
                "geohash": "ttnfv2",
                "has_child": True,
                "has_elderly": False,
                "is_pregnant": False,
                "has_respiratory_condition": True,
                "has_heart_condition": False,
                "commute_mode": "two_wheeler",
                "commute_minutes_per_day": 45,
                "outdoor_work": False,
                "home_size_sqm": 25.0,
                "ceiling_height_m": 2.7,
                "has_purifier": True,
                "purifier_cadr_m3h": 250.0,
                "has_ac": True,
                "cooking_fuel": "png",
                "budget_tier": "low",
                "language": "en",
                "briefing_time": "06:30"
            }
        if user_id not in self.action_logs:
            self.action_logs[user_id] = []

    def get_user_id_by_token(self, token: str) -> Optional[str]:
        return self.sessions.get(token)

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        return self.profiles.get(user_id, {"user_id": user_id, "language": "en", "budget_tier": "low"})

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if user_id not in self.profiles:
            self.profiles[user_id] = {"user_id": user_id}
        for k, v in updates.items():
            if v is not None:
                self.profiles[user_id][k] = v
        return self.profiles[user_id]

    def add_action_log(self, user_id: str, log: Dict[str, Any]) -> None:
        if user_id not in self.action_logs:
            self.action_logs[user_id] = []
        self.action_logs[user_id].append(log)

    def get_action_logs(self, user_id: str) -> List[Dict[str, Any]]:
        return self.action_logs.get(user_id, [])

    def delete_user_data(self, user_id: str) -> bool:
        if user_id in self.profiles:
            del self.profiles[user_id]
        if user_id in self.action_logs:
            del self.action_logs[user_id]
        if user_id in self.consents:
            del self.consents[user_id]
        tokens_to_del = [t for t, u in self.sessions.items() if u == user_id]
        for t in tokens_to_del:
            del self.sessions[t]
        return True

repo = InMemoryRepository()
