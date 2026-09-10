import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from helper.ffmpeg import take_screen_shot

def humanbytes(size):
    """Convert bytes to human-readable format."""
    if not size:
        return ""
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

@Client.on_message(filters.private & filters.command("screenshot"))
async def generate_screenshots(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Please reply to a video file to generate screenshots.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("The replied message is not a valid video or document file.")
    
    m = await message.reply_text("📥 Initializing download...")
    start_time = time.time()
    
    # Progress callback function
    async def progress(current, total):
        now = time.time()
        diff = now - start_time
        # Update every ~2 seconds to avoid Telegram API FloodWait errors
        if round(diff % 2.0) == 0 or current == total:
            percentage = current * 100 / total if total > 0 else 0
            speed = current / diff if diff > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            
            completed = int(percentage / 10)
            bar = "█" * completed + "░" * (10 - completed)
            
            text = (
                f"📥 **Downloading Video...**\n\n"
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
        # Pass the progress callback into download_media
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/",
            progress=progress
        )
        
        if not video_path or not os.path.exists(video_path):
            return await m.edit_text("❌ Failed to download the video file.")
            
        await m.edit_text("🎞️ Generating screenshots via FFmpeg...")
        
        # Timestamps in seconds (e.g., 10s, 30s, 60s)
        timestamps = [10, 30, 60]
        screenshot_paths = []
        
        for ts in timestamps:
            path = await take_screen_shot(video_path, "downloads", ts)
            if path and os.path.exists(path):
                screenshot_paths.append(path)
                
        if not screenshot_paths:
            return await m.edit_text("❌ Failed to extract screenshots from this video format.")
            
        await m.edit_text("📤 Uploading screenshots...")
        
        for idx, img in enumerate(screenshot_paths, start=1):
            await client.send_photo(
                chat_id=message.chat.id,
                photo=img,
                caption=f"📸 Screenshot #{idx}"
            )
            try:
                os.remove(img)
            except:
                pass
                
        await m.delete()
        
    except Exception as e:
        await m.edit_text(f"❌ Error during screenshot generation:\n`{str(e)}`")
    
    finally:
        # Cleanup downloaded video file from server storage
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
