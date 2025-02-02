import logging
import os
import subprocess
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import Message
from pyromod.listen import listen
from config import OWNER_ID

# Set up logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Directory to save files
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global variables to store file paths
global_paths = {
    "thumbnail_path": None,
    "video_path": None,
    "subtitle_path": None,
    "font_path": None
}


@Bot.on_message(filters.command("thumb") & filters.private & filters.user(OWNER_ID))
async def set_thumbnail(client, message: Message):
    """Set a custom thumbnail for the processed file."""
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("⚠️ Reply to an image to set it as a thumbnail.")
        return

    thumbnail_path = os.path.join(UPLOAD_DIR, "thumbnail.jpg")
    await message.reply_to_message.download(file_name=thumbnail_path)
    global_paths["thumbnail_path"] = thumbnail_path
    LOGGER.info(f"Thumbnail saved at: {thumbnail_path}")
    await message.reply_text("✅ Thumbnail set successfully!")


@Bot.on_message(filters.command("marge") & filters.private & filters.user(OWNER_ID))
async def process_video_with_subtitles(client, message: Message):
    """Add subtitles and font to a video."""
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("⚠️ Reply to a video with the /marge command to start processing.")
        return

    try:
        # Download the video
        video_message = message.reply_to_message
        video_path = os.path.join(UPLOAD_DIR, f"{video_message.video.file_id}.mkv")
        await video_message.download(file_name=video_path)
        global_paths["video_path"] = video_path
        LOGGER.info(f"Video downloaded: {video_path}")
        await message.reply_text("✅ Video downloaded. Now reply to this message with the subtitle file using the /sub command.")

    except Exception as e:
        LOGGER.error(f"Error: {str(e)}")
        await message.reply_text(f"❌ Error: {str(e)}")


@Bot.on_message(filters.command("sub") & filters.private & filters.user(OWNER_ID))
async def process_subtitle(client, message: Message):
    """Handle subtitle file."""
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("⚠️ Reply to the previous message with the subtitle file (.srt/.vtt/.ass).")
        return

    try:
        # Download the subtitle file
        subtitle_message = message.reply_to_message
        subtitle_path = os.path.join(UPLOAD_DIR, subtitle_message.document.file_name)
        await subtitle_message.download(file_name=subtitle_path)
        global_paths["subtitle_path"] = subtitle_path
        LOGGER.info(f"Subtitle downloaded: {subtitle_path}")
        await message.reply_text("✅ Subtitle downloaded. Now reply to this message with the font file using the /font command.")

    except Exception as e:
        LOGGER.error(f"Error: {str(e)}")
        await message.reply_text(f"❌ Error: {str(e)}")


@Bot.on_message(filters.command("font") & filters.private & filters.user(OWNER_ID))
async def process_font(client, message: Message):
    """Handle font file."""
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("⚠️ Reply to the previous message with the font file (.ttf/.otf).")
        return

    try:
        # Download the font file
        font_message = message.reply_to_message
        font_path = os.path.join(UPLOAD_DIR, font_message.document.file_name)
        await font_message.download(file_name=font_path)
        global_paths["font_path"] = font_path
        LOGGER.info(f"Font downloaded: {font_path}")

        # Validate that required files exist
        video_path = global_paths.get("video_path")
        subtitle_path = global_paths.get("subtitle_path")
        thumbnail_path = global_paths.get("thumbnail_path")
        if not video_path or not subtitle_path:
            await message.reply_text("⚠️ Missing video or subtitle file. Ensure you've replied with both before processing.")
            return

        # Process the video with subtitle and font
        await message.reply_text("⚙️ Processing video with subtitle and font...")
        output_path = os.path.join(UPLOAD_DIR, f"output_{os.path.basename(video_path)}")
        ffmpeg_command = [
            "ffmpeg",
            "-i", video_path,
            "-i", subtitle_path,
            "-attach", font_path,
            "-metadata:s:t:0", "mimetype=application/x-font-otf",
            "-map", "0",
            "-map", "1",
            "-metadata:s:s:0", "title=HeavenlySubs",
            "-metadata:s:s:0", "language=eng",
            "-disposition:s:s:0", "default",
            "-c", "copy",
            output_path
        ]

        LOGGER.debug(f"Running ffmpeg command: {' '.join(ffmpeg_command)}")
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            LOGGER.error(f"FFmpeg error: {stderr.decode()}")
            await message.reply_text(f"❌ Failed to process video. Error: {stderr.decode()}")
            return

        LOGGER.info(f"Video processed successfully: {output_path}")
        await message.reply_text("✅ Processing complete! Uploading...")

        # Send the processed video
        if thumbnail_path:
            await client.send_document(
                chat_id=message.chat.id,
                document=output_path,
                thumb=thumbnail_path,
                caption="🎥 Here's your processed video!"
            )
        else:
            await client.send_document(
                chat_id=message.chat.id,
                document=output_path,
                caption="🎥 Here's your processed video!"
            )

    except Exception as e:
        LOGGER.error(f"Error: {str(e)}")
        await message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Clean up
        for path in global_paths.values():
            if path and os.path.exists(path):
                os.remove(path)
                LOGGER.info(f"Deleted file: {path}")
