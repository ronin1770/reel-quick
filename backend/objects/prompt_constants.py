"""Prompt name constants and mappings for the backend."""

from __future__ import annotations

from typing import Dict, List

MONTHLY_FIGURES = "monthly_figures.txt"

AI_TYPE_PROMPT_MAP: Dict[str, str] = {
    "MONTHLY_FIGURES": MONTHLY_FIGURES,
}

AI_TYPE_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "MONTHLY_FIGURES": ["given_month", "field_of_excellence"],
}

AI_TYPE_VARIABLE_MAP: Dict[str, Dict[str, str]] = {
    "MONTHLY_FIGURES": {
        "given_month": "GIVEN_MONTH",
        "field_of_excellence": "FIELD_OF_EXCELLENCE",
    }
}

AI_TYPES = sorted(AI_TYPE_PROMPT_MAP.keys())
