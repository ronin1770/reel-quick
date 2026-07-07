"""
    Purpose: The purpose of this file is to create the prompt of the voice clone. This allows use to reuse same voice clone across multiple items.
    It saves computing resources 

    
    Process is: 
    1. Find your favorite actor and download the reference clip from Youtube using https://publer.com/tools/youtube-video-downloader
    2. Save the file as input.mp4
    3. Create the sub-title by uploading the video (input.mp4) to https://turboscribe.ai/transcript
    4. Generate the text file
    5. Let's suppose your favorite actor speaks between 0:31 till 0:41 seconds of the whole downloaded video
    6. Clip input.mp4 and extract audio for above time duration using the FFMPEG
    7. ffmpeg -i input.mp4 -ss 00:00:31 -t 10 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
"""

import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

ref_audio = "output.wav"
ref_text = "I was referring to the original vintage on which the Sherry is based."

#Create the prompt items

prompt_items = model.create_voice_clone_prompt(
    ref_audio=ref_audio,
    ref_text=ref_text,
    x_vector_only_mode=False,
)


input_text = "When you feel like quitting. Remember why you started"

wavs, sr = model.generate_voice_clone(
    text=input_text,
    language="English",
    voice_clone_prompt=prompt_items,
)
sf.write("output_voice_clone_using_prompts.wav", wavs[0], sr)

