"""Preset catalog for sound prompt templates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List
from uuid import uuid4

from backend.objects.sound_prompt_creator import (
    SoundPromptCreator,
    VoiceDesignRequest,
)


class SoundPromptPreset:
    """Provide predefined sound prompt templates and derived instructions."""

    _GENERATION_OPTIONS: Dict[str, Any] = {
        "max_new_tokens": 2048,
        "output_format": "wav",
        "sample_rate": 24000,
        "return_base64": False,
    }

    _PRESETS: Dict[str, Dict[str, Any]] = {
        "alpha_mentor": {
            "display_name": "Alpha Mentor",
            "description": (
                "A dominant, motivational male preset with heavy weight, "
                "slow pacing, and strong pauses."
            ),
            "request_template": {
                "text": (
                    "Discipline is the bridge between who you are and "
                    "who you can become."
                ),
                "language": "en",
                "voice_profile": {
                    "identity": {
                        "gender_presentation": "masculine",
                        "age_impression": "mature",
                        "accent_pronunciation": "neutral_english",
                    },
                    "voice_body": {
                        "pitch": "low",
                        "vocal_weight": "heavy",
                        "roughness_grit": "slight",
                    },
                    "delivery": {
                        "speaking_pace": "slow",
                        "energy_level": "intense",
                        "dramatic_pause_intensity": "strong",
                    },
                    "personality": {
                        "emotional_tone": [
                            "serious",
                            "inspirational",
                            "aggressive",
                        ],
                        "authority_dominance": "commanding",
                        "warmth_coldness": "balanced",
                    },
                },
                "generation_options": deepcopy(_GENERATION_OPTIONS),
            },
        },
        "wise_king": {
            "display_name": "Wise King",
            "description": (
                "A calm, mature, authoritative male preset with warmth "
                "and cinematic pauses."
            ),
            "request_template": {
                "text": "Wisdom is built when a man learns to stay steady in chaos.",
                "language": "en",
                "voice_profile": {
                    "identity": {
                        "gender_presentation": "masculine",
                        "age_impression": "mature",
                        "accent_pronunciation": "neutral_english",
                    },
                    "voice_body": {
                        "pitch": "low",
                        "vocal_weight": "heavy",
                        "roughness_grit": "smooth",
                    },
                    "delivery": {
                        "speaking_pace": "slow",
                        "energy_level": "controlled",
                        "dramatic_pause_intensity": "cinematic",
                    },
                    "personality": {
                        "emotional_tone": ["serious"],
                        "authority_dominance": "balanced",
                        "warmth_coldness": "warm",
                    },
                },
                "generation_options": deepcopy(_GENERATION_OPTIONS),
            },
        },
        "borderline_angry_coach": {
            "display_name": "Borderline Angry Coach",
            "description": (
                "A hard-hitting male preset with intensity, aggression, "
                "and commanding authority."
            ),
            "request_template": {
                "text": (
                    "Excuses are the language of weak discipline. "
                    "Get up and prove your worth."
                ),
                "language": "en",
                "voice_profile": {
                    "identity": {
                        "gender_presentation": "masculine",
                        "age_impression": "young",
                        "accent_pronunciation": "neutral_english",
                    },
                    "voice_body": {
                        "pitch": "low",
                        "vocal_weight": "heavy",
                        "roughness_grit": "rough",
                    },
                    "delivery": {
                        "speaking_pace": "medium",
                        "energy_level": "intense",
                        "dramatic_pause_intensity": "strong",
                    },
                    "personality": {
                        "emotional_tone": ["aggressive", "inspirational"],
                        "authority_dominance": "commanding",
                        "warmth_coldness": "slight_cold",
                    },
                },
                "generation_options": deepcopy(_GENERATION_OPTIONS),
            },
        },
        "dark_cinematic_narrator": {
            "display_name": "Dark Cinematic Narrator",
            "description": (
                "A deep, dark, serious preset with very low pitch "
                "and cinematic pauses."
            ),
            "request_template": {
                "text": "The strongest men are shaped by silence, pressure, and pain.",
                "language": "en",
                "voice_profile": {
                    "identity": {
                        "gender_presentation": "masculine",
                        "age_impression": "mature",
                        "accent_pronunciation": "neutral_english",
                    },
                    "voice_body": {
                        "pitch": "very_low",
                        "vocal_weight": "heavy",
                        "roughness_grit": "slight",
                    },
                    "delivery": {
                        "speaking_pace": "slow",
                        "energy_level": "controlled",
                        "dramatic_pause_intensity": "cinematic",
                    },
                    "personality": {
                        "emotional_tone": ["serious"],
                        "authority_dominance": "dominant",
                        "warmth_coldness": "cold",
                    },
                },
                "generation_options": deepcopy(_GENERATION_OPTIONS),
            },
        },
    }

    @classmethod
    def _build_response_payload(
        cls,
        preset_name: str,
        request_template: Dict[str, Any],
    ) -> Dict[str, Any]:
        request_model = VoiceDesignRequest(**request_template)
        derived_instruction = SoundPromptCreator.build_prompt_from_request(
            request_model
        )
        return {
            "success": True,
            "preset_name": preset_name,
            "request_id": str(uuid4()),
            "derived_instruction": derived_instruction,
        }

    @classmethod
    def _build_preset_item(
        cls,
        preset_name: str,
        preset_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        request_template = deepcopy(preset_data["request_template"])
        response_payload = cls._build_response_payload(
            preset_name=preset_name,
            request_template=request_template,
        )
        return {
            "preset_name": preset_name,
            "display_name": preset_data["display_name"],
            "description": preset_data["description"],
            "request_template": request_template,
            "response_payload": response_payload,
        }

    @classmethod
    def get_presets(cls) -> Dict[str, Any]:
        """Return all available presets as JSON-style dictionary."""
        presets: List[Dict[str, Any]] = [
            cls._build_preset_item(preset_name, preset_data)
            for preset_name, preset_data in cls._PRESETS.items()
        ]
        return {
            "success": True,
            "presets": presets,
        }

    @classmethod
    def get_preset_value(cls, preset_id: str) -> Dict[str, Any]:
        """Return one preset by id."""
        preset_data = cls._PRESETS.get(preset_id)
        if preset_data is None:
            return {
                "success": False,
                "message": f"Preset not found: {preset_id}",
            }
        return {
            "success": True,
            "preset": cls._build_preset_item(preset_id, preset_data),
        }

    @classmethod
    def list_preset_ids(cls) -> List[str]:
        """Return all preset ids."""
        return list(cls._PRESETS.keys())
