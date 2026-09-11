import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

# Dictionary to track active sessions for stream/sample generation
active_stream_sessions = {}

@Client.on_message(filters.private & filters.command("vs", case_sensitive=False))
async def stream_command_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴠɪᴅᴇᴏ ғɪʟᴇ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ꜱᴀᴍᴘʟᴇ ᴄʟɪᴘ.")
    
    reply = message.reply_to_message
    media = reply.video or reply.document
    
    if not media:
        return await message.reply_text("ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴍᴇꜱꜱᴀɢᴇ ɪꜱ ɴᴏᴛ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ ғɪʟᴇ.")
    
    file_name = getattr(media, "file_name", "Sample_Video.mp4")
    video_duration = getattr(media, "duration", 0) or 0
    
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"stream_cancel_{message.chat.id}")]])
    m = await message.reply_text("📥 ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅ ғᴏʀ ꜱᴀᴍᴘʟᴇ ᴠɪᴅᴇᴏ...", reply_markup=markup)
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
                f"📥 **ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...**\n\n"
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
    active_stream_sessions[message.chat.id] = {"task": task, "video_path": None}

    try:
        video_path = await client.download_media(
            message=reply,
            file_name="downloads/",
            progress=progress
        )
        
        if not video_path or not os.path.exists(video_path):
            active_stream_sessions.pop(message.chat.id, None)
            return await m.edit_text("❌ Failed to download the video file.")
        
        # Save session data
        active_stream_sessions[message.chat.id]["video_path"] = video_path
        active_stream_sessions[message.chat.id]["file_name"] = file_name
        active_stream_sessions[message.chat.id]["duration"] = video_duration

        # Present 30s, 60s, and 120s selection buttons
        select_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏱️ 30s", callback_data=f"stream_gen_30_{message.chat.id}"),
                InlineKeyboardButton("⏱️ 60s", callback_data=f"stream_gen_60_{message.chat.id}")
            ],[
                InlineKeyboardButton("⏱️ 120s", callback_data=f"stream_gen_120_{message.chat.id}")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"stream_cancel_{message.chat.id}")
            ]
        ])
        
        await m.edit_text(
            f"✅ **Download Complete!**\n\n"
            f"📁 **File Name:** `{file_name}`\n\n"
            f"👇 **Select your sample duration below:**",
            reply_markup=select_markup
        )
        
    except asyncio.CancelledError:
        await m.edit_text("❌ **Process Cancelled by User.**")
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
        active_stream_sessions.pop(message.chat.id, None)
    except Exception as e:
        await m.edit_text(f"❌ Error during download:\n`{str(e)}`")
        active_stream_sessions.pop(message.chat.id, None)

@Client.on_callback_query(filters.regex(r"^stream_gen_"))
async def stream_generate_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    duration_choice = int(data[2])  # 30, 60, or 120
    chat_id = int(data[3])
    
    if callback_query.message.chat.id != chat_id:
        return await callback_query.answer("This button is not for you!", show_alert=True)
        
    session = active_stream_sessions.get(chat_id)
    if not session or not session.get("video_path"):
        return await callback_query.answer("Session expired. Please send the /stream command again.", show_alert=True)
        
    video_path = session["video_path"]
    file_name = session["file_name"]
    total_duration = session.get("duration", 0)
    
    # Calculate middle timestamp of the video player section
    if total_duration > 0:
        start_time = total_duration // 2
    else:
        start_time = 120  # Fallback if duration metadata is missing
        
    await callback_query.message.edit_text(f"✂️ Generating {duration_choice}-second sample from the middle of the video...")
    
    sample_path = await generate_video_sample(video_path, "downloads", start_time=start_time, duration=duration_choice)
    
    if not sample_path or not os.path.exists(sample_path):
        active_stream_sessions.pop(chat_id, None)
        return await callback_query.message.edit_text("❌ Failed to create sample video clip.")
        
    await callback_query.message.edit_text("📤 Uploading sample video...")
    
    caption_text = (
        f"🎬 **Sample Clip ({duration_choice}s)**\n"
        f"📂 `{file_name}`\n\n"
        f"⚡ **Powered by @Hari_Moviez**"
    )
    
    await client.send_video(
        chat_id=chat_id,
        video=sample_path,
        caption=caption_text,
        supports_streaming=True
    )
    
    # Cleanup files
    try:
        os.remove(sample_path)
        if os.path.exists(video_path):
            os.remove(video_path)
    except:
        pass
        
    active_stream_sessions.pop(chat_id, None)
    try:
        await callback_query.message.delete()
    except:
        pass

@Client.on_callback_query(filters.regex(r"^stream_cancel_"))
async def stream_cancel_callback(client: Client, callback_query: CallbackQuery):
    chat_id = int(callback_query.data.split("_")[-1])
    session = active_stream_sessions.get(chat_id)
    
    if session:
        task = session.get("task")
        if task and not task.done():
            task.cancel()
        video_path = session.get("video_path")
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
        active_stream_sessions.pop(chat_id, None)
        await callback_query.answer("Cancelled successfully!", show_alert=True)
        try:
            await callback_query.message.edit_text("❌ **Process Cancelled by User.**")
        except:
            pass
    else:
        await callback_query.answer("No active process to cancel.", show_alert=True)
