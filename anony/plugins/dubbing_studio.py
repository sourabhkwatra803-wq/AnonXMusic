# -*- coding: utf-8 -*-
import os, glob, shutil, asyncio, subprocess
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from anony import app

PENDING_MEDIA = {}

def _has_media(m: Message):
    if not m: return False, None, False
    if m.video: return True, m.video.file_name or "video.mp4", True
    if m.audio: return True, m.audio.file_name or "audio.mp3", False
    if m.voice: return True, "voice.ogg", False
    if m.document:
        fn = m.document.file_name or "media.mp4"
        ext = os.path.splitext(fn)[1].lower()
        if ext in [".mp4", ".mkv", ".mov", ".avi", ".webm"]: return True, fn, True
        if ext in [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]: return True, fn, False
    return False, None, False

def studio_kb(key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("AI Keep Voice Only (Zero BGM)", callback_data=f"dub|{key}|voice")],
        [InlineKeyboardButton("AI Keep BGM Only (Zero Voice)", callback_data=f"dub|{key}|bgm")],
        [InlineKeyboardButton("Studio Audio Enhancer (Pro Mic)", callback_data=f"dub|{key}|enhance")],
        [InlineKeyboardButton("Dolby Atmos 3D Surround", callback_data=f"dub|{key}|atmos")]
    ])

def _process_studio(in_path: str, out_dir: str, mode: str, is_video: bool, base: str) -> str:
    ext = "mp4" if is_video else "mp3"
    out_path = os.path.join(out_dir, f"{base}_{mode}.{ext}")
    if mode in ("voice", "bgm"):
        wav_in = os.path.join(out_dir, "src.wav")
        sep_dir = os.path.join(out_dir, "stems")
        os.makedirs(sep_dir, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-i", in_path, "-vn", "-ac", "2", "-ar", "44100", wav_in], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["python3", "-m", "demucs.separate", "-n", "htdemucs", "--two-stems=vocals", "-o", sep_dir, wav_in], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stem = "vocals.wav" if mode == "voice" else "no_vocals.wav"
        found = glob.glob(os.path.join(sep_dir, "**", stem), recursive=True)
        if not found: raise RuntimeError("Stem separation failed.")
        polished = os.path.join(out_dir, "clean.wav")
        af = "highpass=f=90,afftdn=nf=-25,equalizer=f=3000:width_type=h:width=900:g=3.5,acompressor=threshold=-18dB:ratio=3,loudnorm=I=-14:TP=-1.0:LRA=11" if mode == "voice" else "loudnorm=I=-14:TP=-1.0:LRA=11"
        subprocess.run(["ffmpeg", "-y", "-i", found[0], "-af", af, polished], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = ["ffmpeg", "-y", "-i", in_path, "-i", polished, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", out_path] if is_video else ["ffmpeg", "-y", "-i", polished, "-c:a", "libmp3lame", "-b:a", "320k", out_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path
    af = "highpass=f=80,afftdn=nf=-28,equalizer=f=130:width_type=h:width=90:g=4,equalizer=f=3200:width_type=h:width=800:g=5,acompressor=threshold=-16dB:ratio=3.5:attack=4:release=60,loudnorm=I=-14:TP=-1.5:LRA=11" if mode == "enhance" else "aecho=0.8:0.88:18|32:0.28|0.20,stereowiden=delay=22:feedback=0.35:crossfeed=0.4:drymix=0.75,equalizer=f=65:width_type=h:width=60:g=6,equalizer=f=10000:width_type=h:width=2500:g=4.5,loudnorm=I=-14:TP=-1.0:LRA=11"
    cmd = ["ffmpeg", "-y", "-i", in_path, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "256k", out_path] if is_video else ["ffmpeg", "-y", "-i", in_path, "-af", af, "-c:a", "libmp3lame", "-b:a", "320k", out_path]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

@app.on_message(filters.command(["studio", "dub", "atmos", "enhance"]), group=-27)
async def studio_command(_, m: Message):
    target = m.reply_to_message if m.reply_to_message else m
    ok, fname, is_vid = _has_media(target)
    if not ok:
        await m.reply_text("<b>Wavy Meta AI Dubbing & Dolby Atmos Studio</b>\nReply to any <b>Video, Audio, or Voice</b> with <code>/studio</code>!")
        m.stop_propagation()
        return
    key = f"{m.chat.id}_{target.id}"
    PENDING_MEDIA[key] = (target, fname, is_vid)
    await m.reply_text(f"<b>Meta AI Studio Ready</b>\nFile: <code>{fname}</code>\nSelect mode:", reply_markup=studio_kb(key))
    m.stop_propagation()

@app.on_callback_query(filters.regex(r"^dub\|"), group=-27)
async def execute_dub_studio(_, cq: CallbackQuery):
    await cq.answer()
    _, key, mode = cq.data.split("|")
    if key not in PENDING_MEDIA: return await cq.message.edit_text("Session expired. Reply with /studio again.")
    target_msg, fname, is_vid = PENDING_MEDIA[key]
    work = f"/tmp/dub_{key}_{mode}"
    os.makedirs(work, exist_ok=True)
    st = await cq.message.edit_text("<b>Running Meta AI Neural Separation (htdemucs)...</b>\n<i>Takes ~15-30s for 100% pure separation!</i>")
    try:
        in_p = await target_msg.download(file_name=os.path.join(work, fname))
        base = os.path.splitext(os.path.basename(in_p))[0]
        out_p = await asyncio.to_thread(_process_studio, in_p, work, mode, is_vid, base)
        if os.path.exists(out_p):
            await st.edit_text("<b>Uploading Studio File...</b>")
            cap = f"<b>Processed via Wavy Meta AI Studio</b> ({mode.upper()})"
            await (cq.message.reply_video(out_p, caption=cap) if is_vid else cq.message.reply_audio(out_p, caption=cap))
            await st.delete()
        else: await st.edit_text("Processing failed.")
    except Exception as e: await st.edit_text(f"Error: <code>{e}</code>")
    finally: shutil.rmtree(work, ignore_errors=True)
    cq.stop_propagation()
