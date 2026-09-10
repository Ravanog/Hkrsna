import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from helper.ffmpeg import take_screen_shot

@Client.on_message(filters.private & filters.command("screenshot"))
async def generate_screenshots(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Please reply to a video file to generate screenshots.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("The replied message is not a valid video or document file.")
    
    m = await message.reply_text("📥 Downloading video to generate screenshots...")
    
    os.makedirs("downloads", exist_ok=True)
    video_path = None
    
    try:
        # Download media safely
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/"
        )
        
        if not video_path or not os.path.exists(video_path):
            return await m.edit_text("❌ Failed to download the video file.")
            
        await m.edit_text("🎞️ Generating screenshots via FFmpeg...")
        
        # Take screenshots at 10s, 30s, and 60s (adjust if video is shorter)
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
        # Cleanup video to save server disk space
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
