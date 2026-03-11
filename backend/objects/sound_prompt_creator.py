"""Sound prompt builder for voice-design style TTS instructions."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# =========================
# Enums
# =========================


class GenderPresentation(str, Enum):
    masculine = "masculine"
    feminine = "feminine"
    neutral = "neutral"


class AgeImpression(str, Enum):
    teen = "teen"
    young = "young"
    mature = "mature"
    elder = "elder"


class AccentPronunciation(str, Enum):
    neutral_english = "neutral_english"
    american_english = "american_english"
    british_english = "british_english"


class Pitch(str, Enum):
    very_low = "very_low"
    low = "low"
    mid = "mid"
    high = "high"


class VocalWeight(str, Enum):
    light = "light"
    medium = "medium"
    heavy = "heavy"
    very_heavy = "very_heavy"


class RoughnessGrit(str, Enum):
    smooth = "smooth"
    slight = "slight"
    rough = "rough"
    gritty = "gritty"


class SpeakingPace(str, Enum):
    very_slow = "very_slow"
    slow = "slow"
    medium = "medium"
    fast = "fast"


class EnergyLevel(str, Enum):
    calm = "calm"
    controlled = "controlled"
    intense = "intense"
    explosive = "explosive"


class DramaticPauseIntensity(str, Enum):
    minimal = "minimal"
    natural = "natural"
    strong = "strong"
    cinematic = "cinematic"


class EmotionalTone(str, Enum):
    serious = "serious"
    inspirational = "inspirational"
    aggressive = "aggressive"


class AuthorityDominance(str, Enum):
    soft = "soft"
    balanced = "balanced"
    dominant = "dominant"
    commanding = "commanding"


class WarmthColdness(str, Enum):
    cold = "cold"
    slight_cold = "slight_cold"
    balanced = "balanced"
    warm = "warm"


# =========================
# Request models
# =========================


class IdentityProfile(BaseModel):
    gender_presentation: GenderPresentation
    age_impression: AgeImpression
    accent_pronunciation: AccentPronunciation


class VoiceBodyProfile(BaseModel):
    pitch: Pitch
    vocal_weight: VocalWeight
    roughness_grit: RoughnessGrit


class DeliveryProfile(BaseModel):
    speaking_pace: SpeakingPace
    energy_level: EnergyLevel
    dramatic_pause_intensity: DramaticPauseIntensity


class PersonalityProfile(BaseModel):
    emotional_tone: List[EmotionalTone] = Field(default_factory=list)
    authority_dominance: AuthorityDominance
    warmth_coldness: WarmthColdness


class VoiceProfile(BaseModel):
    identity: IdentityProfile
    voice_body: VoiceBodyProfile
    delivery: DeliveryProfile
    personality: PersonalityProfile


class GenerationOptions(BaseModel):
    max_new_tokens: int = 2048
    output_format: str = "wav"
    sample_rate: int = 24000
    return_base64: bool = False


class VoiceDesignRequest(BaseModel):
    text: str
    language: str = "en"
    voice_profile: VoiceProfile
    generation_options: Optional[GenerationOptions] = None


class SoundPromptCreator:
    """Build human-readable voice instructions from structured profile inputs."""

    GENDER_MAP: Dict[GenderPresentation, str] = {
        GenderPresentation.masculine: "male",
        GenderPresentation.feminine: "female",
        GenderPresentation.neutral: "neutral",
    }

    AGE_MAP: Dict[AgeImpression, str] = {
        AgeImpression.teen: "young",
        AgeImpression.young: "young adult",
        AgeImpression.mature: "mature",
        AgeImpression.elder: "elder",
    }

    ACCENT_MAP: Dict[AccentPronunciation, str] = {
        AccentPronunciation.neutral_english: "neutral English pronunciation",
        AccentPronunciation.american_english: "American English pronunciation",
        AccentPronunciation.british_english: "British English pronunciation",
    }

    PITCH_MAP: Dict[Pitch, str] = {
        Pitch.very_low: "very low pitch",
        Pitch.low: "low pitch",
        Pitch.mid: "mid-range pitch",
        Pitch.high: "higher pitch",
    }

    WEIGHT_MAP: Dict[VocalWeight, str] = {
        VocalWeight.light: "light vocal weight",
        VocalWeight.medium: "medium vocal weight",
        VocalWeight.heavy: "heavy vocal weight",
        VocalWeight.very_heavy: "very heavy vocal weight",
    }

    GRIT_MAP: Dict[RoughnessGrit, str] = {
        RoughnessGrit.smooth: "a smooth vocal texture",
        RoughnessGrit.slight: "a slight vocal grit",
        RoughnessGrit.rough: "a rough vocal texture",
        RoughnessGrit.gritty: "a gritty, textured vocal quality",
    }

    PACE_MAP: Dict[SpeakingPace, str] = {
        SpeakingPace.very_slow: "a very slow and deliberate pace",
        SpeakingPace.slow: "a slow and deliberate pace",
        SpeakingPace.medium: "a balanced, natural pace",
        SpeakingPace.fast: "a faster, urgent pace",
    }

    ENERGY_MAP: Dict[EnergyLevel, str] = {
        EnergyLevel.calm: "calm and controlled energy",
        EnergyLevel.controlled: "controlled and steady energy",
        EnergyLevel.intense: "intense and emotionally charged energy",
        EnergyLevel.explosive: "explosive and forceful energy",
    }

    PAUSE_MAP: Dict[DramaticPauseIntensity, str] = {
        DramaticPauseIntensity.minimal: "minimal pauses between phrases",
        DramaticPauseIntensity.natural: "natural pauses between phrases",
        DramaticPauseIntensity.strong: "strong dramatic pauses between phrases",
        DramaticPauseIntensity.cinematic: "long, cinematic pauses between phrases",
    }

    AUTHORITY_MAP: Dict[AuthorityDominance, str] = {
        AuthorityDominance.soft: "gentle and restrained authority",
        AuthorityDominance.balanced: "balanced authority",
        AuthorityDominance.dominant: "dominant authority and presence",
        AuthorityDominance.commanding: "commanding authority and powerful presence",
    }

    WARMTH_MAP: Dict[WarmthColdness, str] = {
        WarmthColdness.cold: "a cold and emotionally distant tone",
        WarmthColdness.slight_cold: "a slightly cold, stern emotional texture",
        WarmthColdness.balanced: "a balanced emotional tone",
        WarmthColdness.warm: "a warm and encouraging emotional tone",
    }

    TONE_SENTENCE_MAP: Dict[EmotionalTone, str] = {
        EmotionalTone.serious: "The tone should be serious and focused.",
        EmotionalTone.inspirational: "It should feel motivational and inspirational.",
        EmotionalTone.aggressive: (
            "It should carry controlled aggression, bordering on anger "
            "but never becoming chaotic or shouted."
        ),
    }

    @staticmethod
    def format_tones(tones: List[EmotionalTone]) -> str:
        """Create a readable emotional-tone sentence from tone list."""
        if not tones:
            return "The tone should feel expressive and emotionally intentional."

        unique_tones = list(dict.fromkeys(tones))
        if len(unique_tones) == 1:
            return f"The tone should feel {unique_tones[0].value}."

        if len(unique_tones) == 2:
            return (
                f"The tone should feel {unique_tones[0].value} "
                f"and {unique_tones[1].value}."
            )

        joined = ", ".join(t.value for t in unique_tones[:-1])
        return f"The tone should feel {joined}, and {unique_tones[-1].value}."

    @classmethod
    def build_voice_instruction(cls, profile: VoiceProfile) -> str:
        """Build a high-signal instruction string for the voice engine."""
        identity = profile.identity
        body = profile.voice_body
        delivery = profile.delivery
        personality = profile.personality

        gender_text = cls.GENDER_MAP[identity.gender_presentation]
        age_text = cls.AGE_MAP[identity.age_impression]
        accent_text = cls.ACCENT_MAP[identity.accent_pronunciation]

        pitch_text = cls.PITCH_MAP[body.pitch]
        weight_text = cls.WEIGHT_MAP[body.vocal_weight]
        grit_text = cls.GRIT_MAP[body.roughness_grit]

        pace_text = cls.PACE_MAP[delivery.speaking_pace]
        energy_text = cls.ENERGY_MAP[delivery.energy_level]
        pause_text = cls.PAUSE_MAP[delivery.dramatic_pause_intensity]

        authority_text = cls.AUTHORITY_MAP[personality.authority_dominance]
        warmth_text = cls.WARMTH_MAP[personality.warmth_coldness]

        tones_text = cls.format_tones(personality.emotional_tone)

        lines = [
            f"Speak in a {age_text}, {gender_text} voice with {accent_text}.",
            f"Use {pitch_text}, {weight_text}, and {grit_text}.",
            f"Deliver the speech with {pace_text}, {energy_text}, and {pause_text}.",
            tones_text,
            f"The performance should project {authority_text}.",
            f"Maintain {warmth_text}.",
            "Each word should feel intentional, impactful, and emotionally charged.",
        ]

        if identity.gender_presentation == GenderPresentation.masculine:
            lines.append(
                "The voice should carry strong masculine presence and confidence."
            )

        if body.vocal_weight in {VocalWeight.heavy, VocalWeight.very_heavy}:
            lines.append(
                "Keep the resonance deep and chest-heavy for a powerful presence."
            )

        if personality.authority_dominance in {
            AuthorityDominance.dominant,
            AuthorityDominance.commanding,
        }:
            lines.append(
                "The overall effect should feel like a leader delivering "
                "a powerful wake-up call."
            )

        return " ".join(lines)

    @classmethod
    def build_prompt_from_request(cls, request: VoiceDesignRequest) -> str:
        """Build voice instruction from an end-user request model."""
        return cls.build_voice_instruction(request.voice_profile)

    @classmethod
    def build_tts_payload(cls, request: VoiceDesignRequest) -> Dict[str, object]:
        """Create a TTS-ready payload that includes generated instruction text."""
        generation_options = request.generation_options or GenerationOptions()
        return {
            "text": request.text,
            "language": request.language,
            "instruct": cls.build_voice_instruction(request.voice_profile),
            "max_new_tokens": generation_options.max_new_tokens,
            "output_format": generation_options.output_format,
            "sample_rate": generation_options.sample_rate,
            "return_base64": generation_options.return_base64,
        }
