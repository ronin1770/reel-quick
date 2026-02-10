import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)

input_text = """When you feel like quitting…

remember why you started.
"""

# single inference
wavs, sr = model.generate_custom_voice(
    text=input_text,
    language="English", # Pass `Auto` (or omit) for auto language adaptive; if the target language is known, set it explicitly.
    speaker="Ryan",
    instruct="Emotional, motivational", # Omit if not needed.
)
sf.write("output_custom_voice.wav", wavs[0], sr)
