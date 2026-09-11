import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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

# Dictionary to track active screenshot tasks for cancellation
active_screenshot_tasks = {}

@Client.on_message(filters.private & filters.command(["ss"], case_sensitive=False))
async def generate_screenshots(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ғɪʟᴇ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ꜱᴄʀᴇᴇɴꜱʜᴏᴛꜱ.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴍᴇꜱꜱᴀɢᴇ ɪꜱ ɴᴏᴛ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ ғɪʟᴇ.")
    
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"cancel_screen_{message.chat.id}")]])
    m = await message.reply_text("📥 ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅ...", reply_markup=markup)
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
                f"📥 **ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ ғᴏʀ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ...**\n\n"
                f"[{bar}] {percentage:.1f}%\n\n"
                f"📁 **Size:** {humanbytes(current)} / {humanbytes(total)}\n"
                f"⚡ **Speed:** {humanbytes(speed)}/s\n"
                f"⏱️ **ETA:** {int(eta)}s"
            )
            try:
                await m.edit_text(text, reply_markup=markup)
            except Exception:
                pass

    os.makedirs("downloads", exist_ok=True)
    video_path = None
    
    # Track current task for cancellation
    task = asyncio.current_task()
    active_screenshot_tasks[message.chat.id] = task

    try:
        # Pass the progress callback into download_media
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/",
            progress=progress
        )
        
        if not video_path or not os.path.exists(video_path):
            active_screenshot_tasks.pop(message.chat.id, None)
            return await m.edit_text("❌ Failed to download the video file.")
            
        await m.edit_text("🎞️ ɢᴇɴᴇʀᴀᴛɪɴɢ ꜱᴄʀᴇᴇɴꜱʜᴏᴛꜱ ᴠɪᴀ ᴜᴘʟᴏᴀᴅᴇᴅ ᴠɪᴅᴇᴏ ғɪʟᴇ...")
        
        # Timestamps in seconds (60s, 180s, 300s, 500s)
        timestamps = [60, 180, 300, 500]
        screenshot_paths = []
        
        for ts in timestamps:
            path = await take_screen_shot(video_path, "downloads", ts)
            if path and os.path.exists(path):
                screenshot_paths.append(path)
                
        if not screenshot_paths:
            active_screenshot_tasks.pop(message.chat.id, None)
            return await m.edit_text("❌ Failed to extract screenshots from this video format.")
            
        await m.edit_text("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ꜱᴄʀᴇᴇɴꜱʜᴏᴛꜱ...")
        
        for idx, img in enumerate(screenshot_paths, start=1):
            await client.send_photo(
                chat_id=message.chat.id,
                photo=img,
                caption=f"📸 Screenshot #{idx}\n\n⚡ **Powered by @Hari_Moviez**"
            )
            try:
                os.remove(img)
            except:
                pass
                
        await m.delete()
        
    except asyncio.CancelledError:
        await m.edit_text("❌ **Screenshot Generation Cancelled by User.**")
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
        return
    except Exception as e:
        await m.edit_text(f"❌ Error during screenshot generation:\n`{str(e)}`")
    
    finally:
        active_screenshot_tasks.pop(message.chat.id, None)
        # Cleanup downloaded video file from server storage
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

@Client.on_callback_query(filters.regex(r"^cancel_screen_"))
async def cancel_screenshot_callback(client, callback_query):
    chat_id = int(callback_query.data.split("_")[-1])
    task = active_screenshot_tasks.get(chat_id)
    if task and not task.done():
        task.cancel()
        await callback_query.answer("Screenshot process cancelled successfully!", show_alert=True)
    else:
        await callback_query.answer("No active process to cancel or it already finished.", show_alert=True)
