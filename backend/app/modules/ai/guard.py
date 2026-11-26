import re
from typing import Literal, Tuple

GuardClass = Literal[
    "empty",
    "emergency",
    "medication",
    "injection",
    "off_topic",
    "misinformation_bait",
    "in_scope",
]

_EMERGENCY_PATTERNS = re.compile(
    r"\b(can'?t breathe|cannot breathe|chest pain|lips turning blue|wheezing|shortness of breath|saans nahi|chhati mein dard)\b",
    re.IGNORECASE,
)
_MEDICATION_PATTERNS = re.compile(
    r"\b(which medicine|what medicine|tablet|syrup|antibiotic|inhaler dose|dosage|prescribe|dawai|dawa|goli)\b",
    re.IGNORECASE,
)
_INJECTION_PATTERNS = re.compile(
    r"(ignore previous instructions|ignore all instructions|print your system prompt|reveal your prompt|system prompt)",
    re.IGNORECASE,
)
_MISINFO_PATTERNS = re.compile(
    r"(100%\s*(of\s*)?(pollution|safe|clean)|completely removes|zero risk)",
    re.IGNORECASE,
)
_OFF_TOPIC_PATTERNS = re.compile(
    r"\b(poem|cricket|football|movie|recipe|joke|python code|javascript|stock market|politics|homework)\b",
    re.IGNORECASE,
)


def sanitize_input(text: str, max_len: int = 1000) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text or "")
    return cleaned.strip()[:max_len]


def classify_input(message: str) -> Tuple[GuardClass, str]:
    cleaned = sanitize_input(message)
    if not cleaned:
        return "empty", cleaned
    if _EMERGENCY_PATTERNS.search(cleaned):
        return "emergency", cleaned
    if _INJECTION_PATTERNS.search(cleaned):
        return "injection", cleaned
    if _MEDICATION_PATTERNS.search(cleaned):
        return "medication", cleaned
    if _MISINFO_PATTERNS.search(cleaned):
        return "misinformation_bait", cleaned
    if _OFF_TOPIC_PATTERNS.search(cleaned):
        return "off_topic", cleaned
    return "in_scope", cleaned
