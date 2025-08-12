import os
import subprocess
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import yt_dlp
import openai
import srt

BOT_TOKEN = os.getenv("BOT_TOKEN")
openai.api_key = os.getenv("OPENAI_KEY")

def download_youtube_video(url, output_path):
    ydl_opts = {'format': 'mp4', 'outtmpl': output_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def generate_srt(video_path):
    with open(video_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f, response_format="srt")
    srt_path = video_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(transcript)
    return srt_path

def convert_srt_to_ass(srt_path, ass_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))
    ass_content = """[Script Info]
Title: 2Short Style
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BigYellow,Arial Black,58,&H00FFFF00,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,40,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for sub in subs:
        start = str(sub.start)[:-3]
        end = str(sub.end)[:-3]
        text = sub.content.replace("\n", " ")
        ass_content += f"Dialogue: 0,{start},{end},BigYellow,,0,0,0,,{text}\n"
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

def convert_to_short(video_path, ass_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"scale=720:1280,subtitles='{ass_path}'",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "youtube.com" in text or "youtu.be" in text:
        await update.message.reply_text("⏳ Memproses video...")
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            output_short = os.path.join(tmpdir, "short.mp4")
            ass_path = os.path.join(tmpdir, "sub.ass")

            download_youtube_video(text, video_path)
            srt_path = generate_srt(video_path)
            convert_srt_to_ass(srt_path, ass_path)
            convert_to_short(video_path, ass_path, output_short)

            await update.message.reply_video(video=open(output_short, "rb"))
    else:
        await update.message.reply_text("Kirim link YouTube.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot aktif...")
    app.run_polling()
