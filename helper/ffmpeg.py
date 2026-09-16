import os
import asyncio
import json
from helper.utils import metadata_text

# Global semaphore to queue heavy FFmpeg tasks and protect Koyeb from 100% CPU/RAM spikes
FFMPEG_SEMAPHORE = asyncio.Semaphore(1)


async def rename_audio_tracks(video_file, output_directory, audio_title="Powered by @Hari_Moviez"):
    """
    Updates internal audio track metadata using the user's custom title safely via semaphore queue.
    """
    async with FFMPEG_SEMAPHORE:
        os.makedirs(output_directory, exist_ok=True)
        output_file = os.path.join(output_directory, f"audio_edited_{os.path.basename(video_file)}")
        
        command = [
            "ffmpeg",
            "-i", video_file,
            "-threads", "2",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata:s:a:0", f"title={audio_title}",
            output_file,
            "-y"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return output_file
        except Exception as e:
            print(f"FFmpeg Audio Custom Tag Error: {e}")
            
        return None


async def generate_video_sample(video_file, output_directory, start_time=60, duration=30):
    """
    Generates a fast, high-quality video sample preserving original landscape resolution and codecs.
    """
    async with FFMPEG_SEMAPHORE:
        os.makedirs(output_directory, exist_ok=True)
        out_sample_path = os.path.join(output_directory, f"sample_{os.path.basename(video_file)}")
        
        command = [
            "ffmpeg",
            "-i", video_file,
            "-ss", str(start_time),
            "-t", str(duration),
            "-threads", "2",
            "-c", "copy",
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
    """
    async with FFMPEG_SEMAPHORE:
        out_image_path = os.path.join(output_directory, f"{os.path.basename(video_file)}_{ttl}.jpg")
        
        command = [
            "ffmpeg",
            "-ss", str(ttl),
            "-i", video_file,
            "-threads", "2",
            "-vframes", "1",
            "-q:v", "2",
            out_image_path,
            "-y"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if os.path.exists(out_image_path) and os.path.getsize(out_image_path) > 0:
                return out_image_path
        except Exception as e:
            print(f"FFmpeg Screenshot Error: {e}")
            
        return None
    

async def change_metadata(input_file, output_file, metadata):
    """
    Updates file metadata asynchronously without blocking the event loop or crashing Koyeb.
    """
    async with FFMPEG_SEMAPHORE:
        try:
            author, title, video_title, audio_title, subtitle_title = await metadata_text(metadata)
            
            # Non-blocking ffprobe check using asyncio subprocess
            probe_cmd = ['ffprobe', '-v', 'error', '-show_streams', '-print_format', 'json', input_file]
            probe_process = await asyncio.create_subprocess_exec(
                *probe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await probe_process.communicate()
            
            if probe_process.returncode != 0:
                print(f"FFprobe Error: {stderr.decode()}")
                return False

            data = json.loads(stdout.decode())
            streams = data.get('streams', [])
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-threads', '2',
                '-map', '0',  
                '-c:v', 'copy',  
                '-c:a', 'copy',  
                '-c:s', 'copy',  
                '-metadata', f'title={title}',
                '-metadata', f'author={author}',
            ]

            for stream in streams:
                idx = stream.get("index")
                st_type = stream.get("codec_type")
                if st_type == 'video' and video_title:
                    cmd.extend([f'-metadata:s:{idx}', f'title={video_title}'])
                elif st_type == 'audio' and audio_title:
                    cmd.extend([f'-metadata:s:{idx}', f'title={audio_title}'])
                elif st_type == 'subtitle' and subtitle_title:
                    cmd.extend([f'-metadata:s:{idx}', f'title={subtitle_title}'])

            cmd.extend(['-metadata', f'comment=Added by @Hari_Moviez'])
            cmd.extend(['-f', 'matroska']) 
            cmd.append(output_file)

            # Non-blocking ffmpeg execution
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, err_output = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return True
            else:
                print("FFmpeg Metadata Error:", err_output.decode())
                return False
                
        except Exception as e:
            print(f"Metadata Processing Exception: {e}")
            return False
