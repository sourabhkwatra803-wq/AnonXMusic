import os, re, shutil, asyncio, subprocess
from PIL import Image
import fitz
from docx import Document
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from anony import app

PENDING_FILES = {}

VALID_FORMATS = ["pdf", "docx", "txt", "png", "jpg", "jpeg", "webp", "ico", "mp3", "wav", "ogg", "m4a", "mp4", "gif", "comp"]

def parse_direct_fmt(text: str):
    if not text:
        return None
    words = re.findall(r"[a-z0-9]+", text.lower())
    for w in words:
        if w == "jpeg": return "jpg"
        if w == "word": return "docx"
        if w == "voice": return "ogg"
        if w == "compress": return "comp"
        if w in VALID_FORMATS:
            return w
    return None

def get_file_info(m: Message):
    if not m:
        return None, None
    if m.photo:
        return "image", "photo.jpg"
    if m.video:
        return "video", m.video.file_name or "video.mp4"
    if m.animation:
        return "video", m.animation.file_name or "anim.mp4"
    if m.audio:
        return "audio", m.audio.file_name or "audio.mp3"
    if m.voice:
        return "audio", "voice.ogg"
    if m.document:
        fname = m.document.file_name or "file"
        ext = os.path.splitext(fname)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".ico"]:
            return "image", fname
        if ext in [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".gif"]:
            return "video", fname
        if ext in [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]:
            return "audio", fname
        if ext in [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt"]:
            return "doc", fname
    return None, None

def build_conv_kb(ftype, key):
    if ftype == "image":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 PDF", callback_data=f"cv|{key}|pdf"),
             InlineKeyboardButton("🖼 PNG", callback_data=f"cv|{key}|png")],
            [InlineKeyboardButton("📸 JPG", callback_data=f"cv|{key}|jpg"),
             InlineKeyboardButton("🌐 WEBP", callback_data=f"cv|{key}|webp"),
             InlineKeyboardButton("🎯 ICO", callback_data=f"cv|{key}|ico")]
        ])
    elif ftype == "doc":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 PDF", callback_data=f"cv|{key}|pdf"),
             InlineKeyboardButton("📝 Word (.docx)", callback_data=f"cv|{key}|docx")],
            [InlineKeyboardButton("📃 Text (.txt)", callback_data=f"cv|{key}|txt"),
             InlineKeyboardButton("🖼 PDF to Image", callback_data=f"cv|{key}|png")]
        ])
    elif ftype == "video":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Extract MP3", callback_data=f"cv|{key}|mp3"),
             InlineKeyboardButton("🎞 Convert to GIF", callback_data=f"cv|{key}|gif")],
            [InlineKeyboardButton("🎬 Fast MP4", callback_data=f"cv|{key}|mp4"),
             InlineKeyboardButton("📦 Compress Video", callback_data=f"cv|{key}|comp")]
        ])
    elif ftype == "audio":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 MP3", callback_data=f"cv|{key}|mp3"),
             InlineKeyboardButton("🔊 WAV", callback_data=f"cv|{key}|wav")],
            [InlineKeyboardButton("🎙 Voice (OGG)", callback_data=f"cv|{key}|ogg"),
             InlineKeyboardButton("🎧 M4A", callback_data=f"cv|{key}|m4a")]
        ])

def run_conversion(in_path, out_dir, ftype, target_fmt, base_name):
    out_path = os.path.join(out_dir, f"{base_name}.{target_fmt}")
    in_ext = os.path.splitext(in_path)[1].lower()

    if ftype == "image":
        img = Image.open(in_path)
        if target_fmt in ["jpg", "pdf"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if target_fmt == "pdf":
            img.save(out_path, "PDF", resolution=100.0)
        elif target_fmt == "jpg":
            img.save(out_path, "JPEG", quality=95)
        elif target_fmt == "ico":
            img.save(out_path, "ICO", sizes=[(256, 256)])
        else:
            img.save(out_path, target_fmt.upper())
        return out_path

    elif ftype == "doc":
        if target_fmt == "txt":
            if in_ext == ".pdf":
                doc = fitz.open(in_path)
                text = "\n".join([page.get_text() for page in doc])
            elif in_ext == ".docx":
                d = Document(in_path)
                text = "\n".join([p.text for p in d.paragraphs])
            else:
                text = open(in_path, errors="ignore").read()
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text or "No extractable text found.")
            return out_path
        elif target_fmt == "png" and in_ext == ".pdf":
            doc = fitz.open(in_path)
            pix = doc[0].get_pixmap(dpi=150)
            pix.save(out_path)
            return out_path
        elif target_fmt == "docx" and in_ext == ".pdf":
            doc = fitz.open(in_path)
            d = Document()
            for page in doc:
                d.add_paragraph(page.get_text())
            d.save(out_path)
            return out_path
        else:
            subprocess.run(["libreoffice", "--headless", "--convert-to", target_fmt, "--outdir", out_dir, in_path], check=True)
            for f in os.listdir(out_dir):
                if f.endswith(f".{target_fmt}"):
                    return os.path.join(out_dir, f)

    elif ftype == "video":
        if target_fmt == "mp3":
            subprocess.run(["ffmpeg", "-y", "-i", in_path, "-vn", "-ab", "192k", out_path], check=True)
        elif target_fmt == "gif":
            subprocess.run(["ffmpeg", "-y", "-i", in_path, "-t", "10", "-vf", "fps=12,scale=480:-1:flags=lanczos", out_path], check=True)
        elif target_fmt == "comp":
            out_path = os.path.join(out_dir, f"{base_name}_compressed.mp4")
            subprocess.run(["ffmpeg", "-y", "-i", in_path, "-vcodec", "libx264", "-crf", "28", "-preset", "fast", out_path], check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-i", in_path, "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", out_path], check=True)
        return out_path

    elif ftype == "audio":
        if target_fmt == "ogg":
            subprocess.run(["ffmpeg", "-y", "-i", in_path, "-c:a", "libopus", "-b:a", "64k", out_path], check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-i", in_path, out_path], check=True)
        return out_path

async def process_and_send(reply_target: Message, target_msg: Message, ftype: str, fname: str, target_fmt: str):
    work_dir = f"/tmp/conv_{reply_target.chat.id}_{target_msg.id}_{target_fmt}"
    os.makedirs(work_dir, exist_ok=True)
    status = await reply_target.reply_text(f"⚡ <b>Converting to {target_fmt.upper()}...</b>")
    try:
        in_path = await target_msg.download(file_name=os.path.join(work_dir, fname))
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        out_path = await asyncio.to_thread(run_conversion, in_path, work_dir, ftype, target_fmt, base_name)
        if out_path and os.path.exists(out_path):
            await status.edit_text("📤 <b>Uploading converted file...</b>")
            if target_fmt == "ogg":
                await reply_target.reply_voice(out_path, caption="✅ <b>Converted via Wavy</b>")
            elif target_fmt in ["mp3", "wav", "m4a"]:
                await reply_target.reply_audio(out_path, caption="✅ <b>Converted via Wavy</b>")
            elif target_fmt in ["mp4", "comp"]:
                await reply_target.reply_video(out_path, caption="✅ <b>Converted via Wavy</b>")
            elif target_fmt in ["png", "jpg", "webp"]:
                await reply_target.reply_photo(out_path, caption="✅ <b>Converted via Wavy</b>")
            else:
                await reply_target.reply_document(out_path, caption="✅ <b>Converted via Wavy</b>")
            await status.delete()
        else:
            await status.edit_text("❌ Conversion failed for this file.")
    except Exception as e:
        await status.edit_text(f"❌ Conversion Error: <code>{e}</code>")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

@app.on_message(filters.command(["convert"]) | (filters.private & (filters.photo | filters.document | filters.video | filters.audio | filters.voice)), group=-25)
async def detect_file_convert(_, m: Message):
    target = m.reply_to_message if (m.command and m.reply_to_message) else m
    ftype, fname = get_file_info(target)
    if not ftype:
        if m.command:
            await m.reply_text(
                "🔄 <b>All-in-One File Converter</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Send any <b>Photo, Video, Audio, PDF, or Word (.docx)</b> file directly (or reply with <code>/convert to pdf</code>)!"
            )
            m.stop_propagation()
        return

    direct_fmt = parse_direct_fmt(m.text or m.caption or "")
    if direct_fmt:
        await process_and_send(m, target, ftype, fname, direct_fmt)
        m.stop_propagation()
        return

    key = f"{m.chat.id}_{target.id}"
    PENDING_FILES[key] = (target, ftype, fname)
    await m.reply_text(
        f"🔄 <b>File Detected:</b> <code>{fname}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select your output format below 👇",
        reply_markup=build_conv_kb(ftype, key)
    )
    m.stop_propagation()

@app.on_callback_query(filters.regex(r"^cv\|"), group=-25)
async def execute_convert(_, cq: CallbackQuery):
    await cq.answer()
    _, key, target_fmt = cq.data.split("|")
    if key not in PENDING_FILES:
        return await cq.message.edit_text("⚠️ Session expired. Please send the file again.")
    target_msg, ftype, fname = PENDING_FILES[key]
    await cq.message.delete()
    await process_and_send(cq.message, target_msg, ftype, fname, target_fmt)
    cq.stop_propagation()
