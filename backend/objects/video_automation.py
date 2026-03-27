"""
    Name: video_automation.py
    Description: This class creates videos for provided input 
    Input contains of a json object that advises on:
    - Files in the video
    - Their durations
    - Output file name
    - It uses moviepy to execute
"""

from moviepy import *
#import numpy as np
import json,sys,os,subprocess,tempfile
from config import *
from backend.logger import get_logger


class VideoAutomation:

    def __init__(self, input_json_file):
        self.input_json_file = input_json_file
        self.processing_data = {}
        self.logger = get_logger(name="instagram_reel_creation_video_automation")

    #this method creates the output video
    def process_and_create_output(self):
        #check if processing_data is not {}

        if self.processing_data == {}:
            self.logger.error("Invalid processing data in JSON file. Can't continue.")
            return False
        
        try:
            # Lower process priority to keep the system responsive
            try:
                os.nice(10)
            except Exception:
                pass

            clip_specs = self._read_clip_specs()
            output_file = self.processing_data["output_file_name"]

            self.logger.info(
                "Processing video config. clips=%s output=%s",
                len(clip_specs),
                output_file,
            )
            
            # Resource-friendly settings
            target_width = 1440
            target_size = None
            target_fps = None
            ffmpeg_threads = 1
            ffmpeg_params = ["-filter_threads", "1", "-filter_complex_threads", "1"]
            drop_audio = True

            # Render each clip to an isolated temp folder to prevent cross-job collisions.
            output_root = os.path.abspath(OUTPUT_FOLDER or ".")
            os.makedirs(output_root, exist_ok=True)
            temp_dir = tempfile.mkdtemp(prefix="segments_", dir=output_root)
            temp_files = []
            concat_list_path = None

            # Process each input video according to durations.
            for index, clip_spec in enumerate(clip_specs):
                part_number = clip_spec.get("part_number", index + 1)
                video_filename = clip_spec["file_location"]
                start = clip_spec["start"]
                end = clip_spec["end"]
                if end <= start:
                    self.logger.warning(
                        "Skipping part=%s due to invalid duration start=%s end=%s",
                        part_number,
                        start,
                        end,
                    )
                    continue

                # Construct full path to the video file
                if os.path.isabs(video_filename):
                    video_path = video_filename
                else:
                    video_path = os.path.join(INPUT_FOLDER, video_filename)

                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Clip not found for part={part_number}: {video_path}")

                self.logger.info(
                    "Rendering clip part=%s source=%s start=%.3f end=%.3f",
                    part_number,
                    video_path,
                    start,
                    end,
                )

                # Load and process the clip
                clip = VideoFileClip(video_path)
                if target_fps is None:
                    target_fps = clip.fps or 30
                clip = clip.subclipped(start, end)
                clip = clip.with_effects([vfx.FadeOut(1)]).resized(width=target_width)
                if target_size is None:
                    target_size = clip.size
                elif clip.size != target_size:
                    # Fallback to direct resize to ensure consistent dimensions for concat
                    clip = clip.resized(width=target_size[0], height=target_size[1])
                if drop_audio:
                    clip = clip.without_audio()

                # Write the normalized segment to disk, then close the clip
                temp_file = os.path.join(
                    temp_dir,
                    f"segment_{index:03d}_part_{part_number}.mp4",
                )
                clip.write_videofile(
                    temp_file,
                    codec="libx264",
                    audio=False,
                    fps=target_fps,
                    threads=ffmpeg_threads,
                    ffmpeg_params=ffmpeg_params,
                )
                clip.close()
                temp_files.append(temp_file)

            if not temp_files:
                self.logger.error("No clips were generated from the inputs.")
                return False

            # Concatenate using ffmpeg concat demuxer to avoid loading everything into RAM
            output_path = os.path.join(output_root, output_file)
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, "w") as concat_file:
                for temp_file in temp_files:
                    safe_path = os.path.abspath(temp_file).replace("'", "\\'")
                    concat_file.write(f"file '{safe_path}'\n")

            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                "-threads", str(ffmpeg_threads),
                output_path,
            ]
            result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.logger.warning("ffmpeg concat failed. Falling back to re-encode.")
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c:v", "libx264",
                    "-r", str(target_fps or 30),
                    "-an",
                    "-threads", str(ffmpeg_threads),
                    output_path,
                ]
                result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    self.logger.error("ffmpeg re-encode failed: %s", result.stderr)
                    return False
            return True

        except Exception as e:
            self.logger.exception("Exception in process_and_create_output: %s", str(e))
            return False
        finally:
            # Cleanup temp files/segments and concat list
            for temp_file in temp_files if "temp_files" in locals() else []:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
            if "concat_list_path" in locals() and concat_list_path:
                try:
                    if os.path.exists(concat_list_path):
                        os.remove(concat_list_path)
                except Exception:
                    pass
            if "temp_dir" in locals():
                try:
                    if os.path.isdir(temp_dir):
                        for name in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, name)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        if not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
                except Exception:
                    pass

    def _read_clip_specs(self):
        clips = self.processing_data.get("clips")
        if isinstance(clips, list):
            normalized = []
            for index, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    continue
                file_location = clip.get("file_location")
                if not file_location:
                    continue
                normalized.append(
                    {
                        "part_number": clip.get("part_number", index + 1),
                        "file_location": str(file_location),
                        "start": float(clip.get("start", 0.0)),
                        "end": float(clip.get("end", 0.0)),
                    }
                )
            return normalized

        # Backward compatibility with legacy payload format.
        inputs = self.processing_data.get("inputs", [])
        durations = self.processing_data.get("durations", {})
        normalized = []
        for index, video_filename in enumerate(inputs):
            duration_info = durations.get(str(index))
            if not duration_info:
                continue
            normalized.append(
                {
                    "part_number": index + 1,
                    "file_location": video_filename,
                    "start": float(duration_info.get("start", 0.0)),
                    "end": float(duration_info.get("end", 0.0)),
                }
            )
        return normalized
    
    #This method takes in the json object and creates mapping for video
    def read_video_config(self):
        # Support absolute paths (like temp files) while keeping legacy INPUT_FOLDER behavior.
        if os.path.isabs(self.input_json_file) or os.path.exists(self.input_json_file):
            file_path = self.input_json_file
        else:
            file_path = os.path.join(INPUT_FOLDER, self.input_json_file)

        try:
            with open(file_path, 'r') as file:
                self.processing_data = json.load(file)
                return  True
                
        except Exception as e:
            self.logger.exception("Exception while reading video config: %s", str(e))
            return False

"""if __name__ == "__main__":
    
    inputs = [ "d.json" ]

    for input_json_file in inputs:
        print(f"\n\nProcessing: {input_json_file}\n--------------------\n")
        va = VideoAutomation(input_json_file)
        read = va.read_video_config()

        if not read:
            print(f"Issue read or parsing config file: {input_json_file}")
            sys.exit(1)
        
        created = va.process_and_create_output()

        if not created:
            print(f"Issue creating output file.")
            sys.exit(1)"""
