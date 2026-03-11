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

    texts = [
        """
        Discipline is not punishment.
        It is power.
        Do what weak people refuse to do.
        """,
        """
        You say you want success.
        Then stop negotiating with your excuses.
        """,
        """
        Pain changes men.
        Use it.
        Build from it.
        Rise because of it.
        """
    ]

    instructs = [
        """
        Speak in a deep, powerful male voice with a slow and deliberate pace.
        Heavy tone, authoritative delivery, strong resonance, and controlled aggression.
        Sound wise, dominant, motivational, and intense.
        """,
        """
        Use a deep masculine voice with a steady slow pace.
        Speak like a strong mentor delivering a harsh truth.
        Keep the tone serious, commanding, and slightly angry.
        """,
        """
        Speak in a cinematic deep male voice.
        Slow, heavy, emotionally intense, powerful, wise, and motivational.
        Maintain a low pitch with dramatic pauses and controlled anger.
        """
    ]

    languages = ["English", "English", "English"]

    if "cuda" in device:
        torch.cuda.synchronize()
    t0 = time.time()

    wavs, sr = tts.generate_voice_design(
        text=texts,
        language=languages,
        instruct=instructs,
        max_new_tokens=2048,
    )

    if "cuda" in device:
        torch.cuda.synchronize()
    t1 = time.time()

    print(f"[Batch Motivation Generation] time: {t1 - t0:.3f}s")
    print(f"Sample rate: {sr}")

    for i, wav in enumerate(wavs):
        output_file = f"motivation_quote_{i}.wav"
        sf.write(output_file, wav, sr)
        print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()