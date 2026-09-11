import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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

# Dictionary to track active tasks for cancellation
active_tasks = {}

@Client.on_message(filters.private & filters.command(["sample", "videosample"], case_sensitive=False))
async def generate_sample_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Please reply to a video file to generate a sample clip.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("The replied message is not a valid video or document file.")
    
    # Extract the file name (fall back to a default name if not available)
    file_name = getattr(media, "file_name", "Sample_Video.mp4")
    
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_sample_{message.chat.id}")]])
    m = await message.reply_text("📥 Initializing download for sample generation...", reply_markup=markup)
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
                await m.edit_text(text, reply_markup=markup)
            except Exception:
                pass

    os.makedirs("downloads", exist_ok=True)
    video_path = None
    
    task = asyncio.current_task()
    active_tasks[message.chat.id] = task

    try:
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/",
            progress=progress
        )
        
        if not video_path or not os.path.exists(video_path):
            active_tasks.pop(message.chat.id, None)
            return await m.edit_text("❌ Failed to download the video file.")
            
        await m.edit_text("✂️ Generating 30-second sample clip via FFmpeg...")
        
        sample_path = await generate_video_sample(video_path, "downloads", start_time=60, duration=30)
        
        if not sample_path or not os.path.exists(sample_path):
            active_tasks.pop(message.chat.id, None)
            return await m.edit_text("❌ Failed to create sample video clip.")
            
        await m.edit_text("📤 Uploading sample video...")
        
        # Caption includes the filename and your branding
        caption_text = (
            f"🎬 **Sample / Teaser Clip**\n"
            f"📂 **File Name:** `{file_name}`\n\n"
            f"⚡ **Powered by @Hari_Moviez**"
        )
        
        await client.send_video(
            chat_id=message.chat.id,
            video=sample_path,
            caption=caption_text,
            supports_streaming=True
        )
        
        try:
            os.remove(sample_path)
        except:
            pass
            
        await m.delete()
        
    except asyncio.CancelledError:
        await m.edit_text("❌ **Process Cancelled by User.**")
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
        return
    except Exception as e:
        await m.edit_text(f"❌ Error during sample generation:\n`{str(e)}`")
    
    finally:
        active_tasks.pop(message.chat.id, None)
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

@Client.on_callback_query(filters.regex(r"^cancel_sample_"))
async def cancel_sample_callback(client, callback_query):
    chat_id = int(callback_query.data.split("_")[-1])
    task = active_tasks.get(chat_id)
    if task and not task.done():
        task.cancel()
        await callback_query.answer("Process cancelled successfully!", show_alert=True)
    else:
        await callback_query.answer("No active process to cancel or it already finished.", show_alert=True)
