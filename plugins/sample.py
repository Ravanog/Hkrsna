import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from helper.ffmpeg import generate_video_sample

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

@Client.on_message(filters.private & filters.command("sample"))
async def generate_sample_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Please reply to a video file to generate a sample clip.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("The replied message is not a valid video or document file.")
    
    m = await message.reply_text("📥 Initializing download for sample generation...")
    start_time = time.time()
    
    async def progress(current, total):
        now = time.time()
        diff = now - start_time
        if round(diff % 2.0) == 0 or current == total:
            percentage = current * 100 / total if total > 0 else 0
            speed = current / diff if diff > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            
            completed = int(percentage / 10)
            bar = "█" * completed + "░" * (10 - completed)
            
            text = (
                f"📥 **Downloading for Sample...**\n\n"
                f"[{bar}] {percentage:.1f}%\n\n"
                f"📁 **Size:** {humanbytes(current)} / {humanbytes(total)}\n"
                f"⚡ **Speed:** {humanbytes(speed)}/s\n"
                f"⏱️ **ETA:** {int(eta)}s"
            )
            try:
                await m.edit_text(text)
            except Exception:
                pass

    os.makedirs("downloads", exist_ok=True)
    video_path = None
    
    try:
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/",
            progress=progress
        )
        
        if not video_path or not os.path.exists(video_path):
            return await m.edit_text("❌ Failed to download the video file.")
            
        await m.edit_text("✂️ Generating 30-second sample clip via FFmpeg...")
        
        # Generates a 30-second sample starting at 60 seconds in
        sample_path = await generate_video_sample(video_path, "downloads", start_time=60, duration=30)
        
        if not sample_path or not os.path.exists(sample_path):
            return await m.edit_text("❌ Failed to create sample video clip.")
            
        await m.edit_text("📤 Uploading sample video...")
        
        await client.send_video(
            chat_id=message.chat.id,
            video=sample_path,
            caption="🎬 **Sample / Teaser Clip**\n⚡ **Powered by @Hari_Moviez**",
            supports_streaming=True
        )
        
        # Clean up files
        try:
            os.remove(sample_path)
        except:
            pass
            
        await m.delete()
        
    except Exception as e:
        await m.edit_text(f"❌ Error during sample generation:\n`{str(e)}`")
    
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
