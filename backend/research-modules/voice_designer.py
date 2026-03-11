import time
import torch
import soundfile as sf

from qwen_tts import Qwen3TTSModel


def main():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model_path = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"

    tts = Qwen3TTSModel.from_pretrained(
        model_path,
        device_map=device,
        dtype=torch.bfloat16 if "cuda" in device else torch.float32,
        attn_implementation="flash_attention_2" if "cuda" in device else "eager",
    )

    # Your motivational quote text
    text = """
    Listen carefully.

    Nobody is coming to save you.

    Not your friends.
    Not your family.
    Not the world.

    If you want power...
    build yourself.

    If you want respect...
    earn it.

    Stand up.
    Fight harder.
    Become the man they cannot ignore.
    """

    # Custom voice design prompt
    instruct = """
    Speak in a deep, powerful male voice with a slow and deliberate pace.
    The tone should be heavy, authoritative, commanding, and full of wisdom.
    Each word must feel intentional, impactful, and emotionally charged.
    The voice should carry strong masculine energy, presence, and dominance.
    It should sound motivational with controlled aggression, bordering on anger,
    but never chaotic or shouting. Maintain a low pitch, strong resonance, and
    dramatic pauses between phrases. The overall effect should feel like a wise,
    battle-hardened leader giving a powerful wake-up call.
    """

    if "cuda" in device:
        torch.cuda.synchronize()
    t0 = time.time()

    wavs, sr = tts.generate_voice_design(
        text=text,
        language="English",
        instruct=instruct,
        max_new_tokens=2048,
    )

    if "cuda" in device:
        torch.cuda.synchronize()
    t1 = time.time()

    print(f"[Motivational Voice Generation] time: {t1 - t0:.3f}s")
    print(f"Sample rate: {sr}")

    output_file = "motivational_alpha_male_voice.wav"
    sf.write(output_file, wavs[0], sr)
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()