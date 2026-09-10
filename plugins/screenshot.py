import os
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message
from helper.ffmpeg import take_screen_shot

@Client.on_message(filters.private & filters.command("screenshot"))
async def generate_screenshots(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video and not message.reply_to_message.document:
        return await message.reply_text("Please reply to a video file to generate screenshots.")
    
    m = await message.reply_text("Downloading video to generate screenshots...")
    
    # Create a temporary directory
    os.makedirs("downloads", exist_ok=True)
    
    try:
        # Download the media file
        video_path = await client.download_media(
            message.reply_to_message,
            file_name="downloads/"
        )
        
        await m.edit_text("Generating screenshots...")
        
        # Define timestamps to capture screenshots (e.g., at 10s, 30s, 60s)
        # You can also parse video duration dynamically if needed
        timestamps = [10, 30, 60] 
        screenshot_paths = []
        
        for ts in timestamps:
            path = await take_screen_shot(video_path, "downloads", ts)
            if path:
                screenshot_paths.append(path)
                
        if not screenshot_paths:
            return await m.edit_text("Failed to generate screenshots.")
            
        await m.edit_text("Uploading screenshots...")
        
        # Send the generated screenshots back to the user
        for img in screenshot_paths:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=img,
                caption=f"Screenshot at timestamp"
            )
            os.remove(img) # Clean up image file
            
        # Clean up video file
        if os.path.exists(video_path):
            os.remove(video_path)
            
        await m.delete()
        
    except Exception as e:
        await m.edit_text(f"An error occurred: {str(e)}")
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)
