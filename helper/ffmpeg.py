import os
import asyncio
import os, time, asyncio, subprocess, json
from helper.utils import metadata_text


async def generate_video_sample(video_file, output_directory, start_time=60, duration=30):
    """
    Generates a short video sample/teaser using ffmpeg.
    :param video_file: Path to the original video file
    :param output_directory: Directory to save the sample
    :param start_time: Where to start the sample clip in seconds
    :param duration: Duration of the sample clip in seconds
    """
    os.makedirs(output_directory, exist_ok=True)
    out_sample_path = os.path.join(output_directory, f"sample_{os.path.basename(video_file)}")
    
    # FFmpeg command to cut a sample clip quickly and re-encode/copy streams safely
    command = [
        "ffmpeg",
        "-ss", str(start_time),
        "-i", video_file,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        out_sample_path,
        "-y"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if os.path.exists(out_sample_path) and os.path.getsize(out_sample_path) > 0:
            return out_sample_path
    except Exception as e:
        print(f"FFmpeg Sample Error: {e}")
        
    return None
    

async def take_screen_shot(video_file, output_directory, ttl):
    """
    Takes a screenshot from a video file using ffmpeg.
    :param video_file: Path to the video file
    :param output_directory: Where to save the screenshot
    :param ttl: Time in seconds (timestamp) to take the screenshot
    """
    out_image_path = os.path.join(output_directory, f"{os.path.basename(video_file)}_{ttl}.jpg")
    
    # FFmpeg command to extract a frame at a specific timestamp (ttl)
    command = [
        "ffmpeg",
        "-ss", str(ttl),
        "-i", video_file,
        "-vframes", "1",
        "-q:v", "2",
        out_image_path,
        "-y"
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    
    if os.path.exists(out_image_path):
        return out_image_path
    return None
    
async def change_metadata(input_file, output_file, metadata):
    author, title, video_title, audio_title, subtitle_title = await metadata_text(metadata)
    output = subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-print_format', 'json', input_file])
    data = json.loads(output)
    streams = data['streams']
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-map', '0',  # Map all streams
        '-c:v', 'copy',  # Copy video stream
        '-c:a', 'copy',  # Copy audio stream
        '-c:s', 'copy',  # Copy subtitles stream
        '-metadata', f'title={title}',
        '-metadata', f'author={author}',
    ]

    # Add title to video stream
    for stream in streams:
        if stream['codec_type'] == 'video' and video_title:
            cmd.extend([f'-metadata:s:{stream["index"]}', f'title={video_title}'])
        elif stream['codec_type'] == 'audio' and audio_title:
            cmd.extend([f'-metadata:s:{stream["index"]}', f'title={audio_title}'])
        elif stream['codec_type'] == 'subtitle' and subtitle_title:
            cmd.extend([f'-metadata:s:{stream["index"]}', f'title={subtitle_title}'])

    cmd.extend(['-metadata', f'comment=Added by @Hari_Moviez'])
    cmd.extend(['-f', 'matroska']) # support all format 
    cmd.append(output_file)
    print(cmd)
    
    # Execute the command
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("FFmpeg Error:", e.stderr)
        return False
