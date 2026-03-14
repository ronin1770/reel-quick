"""Custom sound designer object for generating output audio files."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from dotenv import find_dotenv, load_dotenv

try:
    from logger import get_logger
except ImportError:  # pragma: no cover - fallback when imported as package
    from backend.logger import get_logger


class CustomSoundDesigner:
    """Generate custom voice-design output files with reusable singleton model."""

    _MODEL: Optional[Any] = None
    _MODEL_LOCK = Lock()
    _DEVICE: Optional[str] = None

    _MODEL_NAME = os.getenv(
        "VOICE_DESIGN_MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    )
    _DEFAULT_LANGUAGE = os.getenv("VOICE_DESIGN_LANGUAGE", "English")
    _DEFAULT_MAX_NEW_TOKENS = int(os.getenv("VOICE_DESIGN_MAX_NEW_TOKENS", "2048"))
    _DEFAULT_OUTPUT_FORMAT = "wav"
    _OUTPUT_DIR_ENV = "SOUND_DESIGNER_FILES"
    _OUTPUT_DIR_FALLBACK = "./sound_designer_files/"

    _logger = get_logger(name="instagram_reel_creation_custom_sound_designer")

    @classmethod
    def create_sound(
        cls,
        request_id: str,
        input_text: str,
        instructions: str,
        *,
        language: str = _DEFAULT_LANGUAGE,
        max_new_tokens: int = _DEFAULT_MAX_NEW_TOKENS,
        output_format: str = _DEFAULT_OUTPUT_FORMAT,
    ) -> Dict[str, Any]:
        """Create sound output file and return structured pass/fail response."""
        safe_request_id = str(request_id)
        output_file: Optional[Path] = None

        try:
            safe_request_id = cls._sanitize_request_id(request_id)
            text = cls._normalize_text(input_text, field_name="input_text")
            instruct = cls._normalize_text(instructions, field_name="instructions")
            normalized_language = cls._normalize_text(language, field_name="language")
            normalized_max_tokens = cls._normalize_max_new_tokens(max_new_tokens)
            normalized_format = cls._normalize_output_format(output_format)

            output_file = cls._build_output_path(safe_request_id, normalized_format)

            wavs, sample_rate = cls._generate_audio(
                text=text,
                language=normalized_language,
                instructions=instruct,
                max_new_tokens=normalized_max_tokens,
            )
            cls._write_output_file(
                wav=wavs[0],
                sample_rate=sample_rate,
                output_path=output_file,
                output_format=normalized_format,
            )

            return {
                "status": "pass",
                "description": "Sound file created successfully.",
                "request_id": safe_request_id,
                "instructions": instruct,
                "output_file": str(output_file),
            }
        except Exception as exc:
            cls._logger.exception(
                "Custom sound creation failed request_id=%s output_file=%s",
                request_id,
                str(output_file) if output_file else None,
            )
            return {
                "status": "fail",
                "description": str(exc),
                "request_id": safe_request_id,
                "instructions": str(instructions),
                "output_file": str(output_file) if output_file else None,
            }

    @classmethod
    def _sanitize_request_id(cls, request_id: str) -> str:
        raw = str(request_id).strip()
        if not raw:
            raise ValueError("request_id is required")
        sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("._-")
        if not sanitized:
            raise ValueError("request_id is invalid after sanitization")
        return sanitized[:120]

    @classmethod
    def _normalize_text(cls, value: str, *, field_name: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")
        return normalized

    @classmethod
    def _normalize_max_new_tokens(cls, max_new_tokens: int) -> int:
        if not isinstance(max_new_tokens, int):
            raise ValueError("max_new_tokens must be an integer")
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be >= 1")
        return max_new_tokens

    @classmethod
    def _normalize_output_format(cls, output_format: str) -> str:
        normalized = str(output_format).strip().lower()
        if normalized not in {"wav", "mp3"}:
            raise ValueError("output_format must be one of: wav, mp3")
        return normalized

    @classmethod
    def _resolve_output_dir(cls) -> Path:
        load_dotenv(find_dotenv())
        output_root = os.getenv(cls._OUTPUT_DIR_ENV, cls._OUTPUT_DIR_FALLBACK)
        path = Path(output_root)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def _build_output_path(cls, request_id: str, output_format: str) -> Path:
        output_dir = cls._resolve_output_dir()
        return (output_dir / f"{request_id}.{output_format}").resolve()

    @classmethod
    def _get_model(cls) -> Any:
        if cls._MODEL is not None:
            return cls._MODEL

        with cls._MODEL_LOCK:
            if cls._MODEL is not None:
                return cls._MODEL

            import torch
            from qwen_tts import Qwen3TTSModel

            configured_device = os.getenv("VOICE_DESIGN_DEVICE")
            if configured_device:
                device = configured_device
            else:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"

            cls._MODEL = Qwen3TTSModel.from_pretrained(
                cls._MODEL_NAME,
                device_map=device,
                dtype=torch.bfloat16 if "cuda" in device else torch.float32,
            )
            cls._DEVICE = device
            cls._logger.info(
                "Loaded voice-design model model=%s device=%s",
                cls._MODEL_NAME,
                device,
            )

        return cls._MODEL

    @classmethod
    def _generate_audio(
        cls,
        *,
        text: str,
        language: str,
        instructions: str,
        max_new_tokens: int,
    ) -> Any:
        import torch

        tts = cls._get_model()

        if cls._DEVICE and "cuda" in cls._DEVICE and torch.cuda.is_available():
            torch.cuda.synchronize()

        wavs, sample_rate = tts.generate_voice_design(
            text=text,
            language=language,
            instruct=instructions,
            max_new_tokens=max_new_tokens,
        )

        if cls._DEVICE and "cuda" in cls._DEVICE and torch.cuda.is_available():
            torch.cuda.synchronize()

        if not wavs:
            raise RuntimeError("No audio output generated by model")
        return wavs, sample_rate

    @classmethod
    def _write_output_file(
        cls,
        *,
        wav: Any,
        sample_rate: int,
        output_path: Path,
        output_format: str,
    ) -> None:
        import soundfile as sf

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "wav":
            sf.write(str(output_path), wav, sample_rate)
            return

        if output_format != "mp3":
            raise ValueError(f"Unsupported output format: {output_format}")

        temp_wav_path = output_path.with_suffix(".tmp.wav")
        try:
            sf.write(str(temp_wav_path), wav, sample_rate)
            command = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(temp_wav_path),
                str(output_path),
            ]
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ffmpeg is not installed or not available in PATH") from exc
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(
                f"ffmpeg conversion failed: {details or 'unknown ffmpeg error'}"
            ) from exc
        finally:
            if temp_wav_path.exists():
                temp_wav_path.unlink(missing_ok=True)

