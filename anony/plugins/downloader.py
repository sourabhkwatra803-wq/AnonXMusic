import os
import re
import sys
import asyncio
import urllib.parse
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from anony import app

URL_REGEX = r"(https?://(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?://(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,})"
URL_CACHE = {}

@app.on_message(filters.regex(URL_REGEX) & ~filters.command(["play", "vplay", "cplay", "cvplay", "qr"]))
async def link_handler(_, m: Message):
    match = re.search(URL_REGEX, m.text or "")
    if not match:
        return
    url = match.group(0)
    key = f"{m.chat.id}_{m.id}"
    URL_CACHE[key] = url

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 1080p", callback_data=f"dl|1080|{key}"),
            InlineKeyboardButton("🎬 720p", callback_data=f"dl|720|{key}")
        ],
        [
            InlineKeyboardButton("🎬 480p", callback_data=f"dl|480|{key}"),
            InlineKeyboardButton("🎬 360p", callback_data=f"dl|360|{key}")
        ],
        [
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"dl|audio|{key}")
        ]
    ])
    await m.reply_text("📥 **Download karne ke liye quality chunein:**", reply_markup=buttons)

@app.on_callback_query(filters.regex(r"^dl\|"))
async def download_callback(_, cb: CallbackQuery):
    _, quality, key = cb.data.split("|")
    url = URL_CACHE.get(key)
    if not url:
        return await cb.answer("❌ Link expire ho gaya, dobara bhejein!", show_alert=True)

    await cb.answer("⏳ Download shuru ho raha hai...")
    msg = await cb.message.edit_text(f"⏳ **{quality}** mein download ho raha hai, kripya intezaar karein...")

    os.makedirs("downloads", exist_ok=True)
    out_tmpl = f"downloads/{cb.id}_%(title).40s.%(ext)s"
    cookie_arg = "--cookies anony/cookies/cookies.txt" if os.path.exists("anony/cookies/cookies.txt") else ""

    if quality == "audio":
        cmd = f'"{sys.executable}" -m yt_dlp {cookie_arg} -x --audio-format mp3 -o "{out_tmpl}" "{url}"'
    else:
        cmd = f'"{sys.executable}" -m yt_dlp {cookie_arg} -f "bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best" --merge-output-format mp4 -o "{out_tmpl}" "{url}"'

    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()

    downloaded_file = None
    for f in os.listdir("downloads"):
        if f.startswith(f"{cb.id}_"):
            downloaded_file = os.path.join("downloads", f)
            break

    if not downloaded_file or not os.path.exists(downloaded_file):
        err_text = stderr.decode("utf-8", errors="ignore").strip().splitlines()
        last_err = err_text[-1] if err_text else "Unknown error"
        return await msg.edit_text(f"❌ Download fail ho gaya:\n`{last_err}`")

    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
    if file_size_mb > 49:
        os.remove(downloaded_file)
        return await msg.edit_text(f"❌ File size **{file_size_mb:.1f} MB** hai (50 MB se zyada). Kripya kam quality (480p/360p) chunein.")

    await msg.edit_text("📤 Telegram par upload ho raha hai...")
    try:
        if quality == "audio":
            await cb.message.reply_audio(downloaded_file)
        else:
            await cb.message.reply_video(downloaded_file)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Upload error: `{e}`")
    finally:
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

@app.on_message(filters.command(["dl", "download"]))
async def dl_cmd_handler(_, m: Message):
    if len(m.command) < 2 and not m.reply_to_message:
        return await m.reply_text(
            "📥 **All-in-One Video & Audio Downloader**\n\n"
            "• **YouTube, Instagram Reels, Facebook, X (Twitter)** ka koi bhi link seedha chat mein bhejein ya `/dl <link>` likhein.\n"
            "• Quality chunein (**1080p, 720p, 480p, 360p**) ya **Audio (MP3)**!"
        )
    text = m.text.split(None, 1)[1] if len(m.command) > 1 else (m.reply_to_message.text or "")
    m.text = text
    await link_handler(_, m)

@app.on_message(filters.command("mp3"))
async def video_to_mp3(_, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.video or m.reply_to_message.document or m.reply_to_message.audio):
        return await m.reply_text("🎵 Kisi bhi **Video** par reply karke `/mp3` likhein, main uska MP3 audio nikal dunga!")
    msg = await m.reply_text("⏳ Video se MP3 banaya ja raha hai...")
    os.makedirs("downloads", exist_ok=True)
    in_file = await m.reply_to_message.download(file_name=f"downloads/in_{m.id}")
    out_file = f"downloads/audio_{m.id}.mp3"
    proc = await asyncio.create_subprocess_shell(
        f'ffmpeg -y -i "{in_file}" -vn -ab 192k -ar 44100 "{out_file}"',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    try:
        if os.path.exists(out_file):
            await m.reply_audio(out_file, caption="🎵 **Converted to MP3**")
            await msg.delete()
        else:
            await msg.edit_text("❌ MP3 conversion fail ho gaya.")
    finally:
        for f in (in_file, out_file):
            if f and os.path.exists(f):
                os.remove(f)

@app.on_message(filters.command("qr"))
async def qr_generator(_, m: Message):
    if len(m.command) < 2 and not m.reply_to_message:
        return await m.reply_text("🔲 QR Code banane ke liye likhein: `/qr <text ya link>`")
    data = m.text.split(None, 1)[1] if len(m.command) > 1 else (m.reply_to_message.text or "")
    encoded = urllib.parse.quote(data)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={encoded}"
    await m.reply_photo(qr_url, caption=f"🔲 **QR Code Generated**\n`{data[:60]}`")


import urllib.request
import json
from PIL import Image

@app.on_message(filters.command(["lyrics", "lyric"]))
async def lyrics_finder(_, m: Message):
    if len(m.command) < 2:
        return await m.reply_text("📝 Gaane ke lyrics dekhne ke liye likhein: `/lyrics <gaane ka naam>`")
    query = m.text.split(None, 1)[1]
    msg = await m.reply_text(f"🔍 **{query}** ke lyrics dhoondhe ja rahe hain...")
    try:
        q = urllib.parse.quote(query)
        req = urllib.request.urlopen(f"https://lrclib.net/api/search?q={q}", timeout=10)
        data = json.loads(req.read().decode("utf-8"))
        if not data:
            return await msg.edit_text("❌ Is gaane ke lyrics nahi mile, thoda sahi naam likh kar try karein.")
        song = data[0]
        title = song.get("trackName", query)
        artist = song.get("artistName", "")
        lyrics = song.get("plainLyrics") or "Lyrics available nahi hain."
        if len(lyrics) > 3800:
            lyrics = lyrics[:3800] + "\n..."
        await msg.edit_text(f"🎵 **{title}** — *{artist}*\n\n{lyrics}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")

@app.on_message(filters.command(["sticker", "kang"]))
async def photo_to_sticker(_, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.document):
        return await m.reply_text("🖼️ Kisi bhi **Photo** par reply karke `/sticker` likhein!")
    msg = await m.reply_text("⏳ Sticker banaya ja raha hai...")
    os.makedirs("downloads", exist_ok=True)
    in_p = await m.reply_to_message.download(file_name=f"downloads/stk_in_{m.id}.jpg")
    out_p = f"downloads/stk_out_{m.id}.webp"
    try:
        im = Image.open(in_p).convert("RGBA")
        im.thumbnail((512, 512))
        im.save(out_p, "WEBP")
        await m.reply_sticker(out_p)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")
    finally:
        for f in (in_p, out_p):
            if f and os.path.exists(f):
                os.remove(f)

@app.on_message(filters.command(["photo", "toimg"]))
async def sticker_to_photo(_, m: Message):
    if not m.reply_to_message or not m.reply_to_message.sticker:
        return await m.reply_text("🖼️ Kisi bhi **Sticker** par reply karke `/photo` likhein!")
    if m.reply_to_message.sticker.is_animated or m.reply_to_message.sticker.is_video:
        return await m.reply_text("❌ Animated/Video sticker ko photo mein nahi badal sakte, normal sticker par try karein.")
    msg = await m.reply_text("⏳ Photo banayi ja rahi hai...")
    os.makedirs("downloads", exist_ok=True)
    in_p = await m.reply_to_message.download(file_name=f"downloads/img_in_{m.id}.webp")
    out_p = f"downloads/img_out_{m.id}.png"
    try:
        im = Image.open(in_p).convert("RGBA")
        im.save(out_p, "PNG")
        await m.reply_photo(out_p, caption="🖼️ **Converted to Photo**")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`")
    finally:
        for f in (in_p, out_p):
            if f and os.path.exists(f):
                os.remove(f)

@app.on_callback_query(filters.regex(r"^feat_"))
async def feature_menu_cb(_, cb: CallbackQuery):
    action = cb.data.split("_", 1)[1]

    menu_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 AI Video Subtitles (Top)", callback_data="feat_sub")
        ],
        [
            InlineKeyboardButton("📥 Video Downloader", callback_data="feat_dl"),
            InlineKeyboardButton("🎵 Video to MP3", callback_data="feat_mp3")
        ],
        [
            InlineKeyboardButton("📝 Song Lyrics", callback_data="feat_lyrics"),
            InlineKeyboardButton("🖼️ Sticker & Photo", callback_data="feat_stk")
        ],
        [
            InlineKeyboardButton("🔲 QR Code Maker", callback_data="feat_qr"),
            InlineKeyboardButton("🎧 VC Music Player", callback_data="feat_music")
        ],
        [
            InlineKeyboardButton("📖 How to Use (Step-by-Step Guide)", callback_data="feat_guide")
        ]
    ])
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to All Features", callback_data="feat_menu")]])

    if action == "menu":
        await cb.message.edit_text(
            "✨ **𝗪𝗔𝗩𝗬 — 𝗔𝗟𝗟-𝗜𝗡-𝗢𝗡𝗘 𝗙𝗘𝗔𝗧𝗨𝗥𝗘𝗦** ✨\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Neeche diye gaye kisi bhi button par tap karein aur dekhein bot kya-kya kar sakta hai 👇",
            reply_markup=menu_kb
        )
    elif action == "guide":
        await cb.message.edit_text(
            "📖 **𝗦𝗧𝗘𝗣-𝗕𝗬-𝗦𝗧𝗘𝗣 𝗨𝗦𝗘𝗥 𝗚𝗨𝗜𝗗𝗘**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎬 **𝟭. 𝗔𝗜 𝗩𝗶𝗱𝗲𝗼 𝗦𝘂𝗯𝘁𝗶𝘁𝗹𝗲𝘀**\n"
            "   ▸ Koi bhi video bot ko bhejein\n"
            "   ▸ Us video par **Reply** karke `/sub` likhein\n"
            "   ▸ **English / Hindi / Hinglish** chunein\n\n"
            "📥 **𝟮. 𝗦𝗼𝗰𝗶𝗮𝗹 𝗠𝗲𝗱𝗶𝗮 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿**\n"
            "   ▸ YouTube, Instagram Reel, FB ya X ka link bhejein\n"
            "   ▸ Quality (**1080p / 720p / MP3**) par tap karein\n\n"
            "🎵 **𝟯. 𝗩𝗶𝗱𝗲𝗼 𝘁𝗼 𝗠𝗣𝟯**\n"
            "   ▸ Kisi bhi video par **Reply** karke `/mp3` likhein\n\n"
            "🎧 **𝟰. 𝗚𝗿𝗼𝘂𝗽 𝗩𝗖 𝗠𝘂𝘀𝗶𝗰 & 𝗩𝗶𝗱𝗲𝗼**\n"
            "   ▸ Group mein Voice Chat (VC) start karein\n"
            "   ▸ `/play <song>` ya `/vplay <video>` likhein\n"
            "   ▸ Ya kisi bheji gayi video par reply karke `/vplay` likhein\n\n"
            "🖼️ **𝟱. 𝗦𝘁𝗶𝗰𝗸𝗲𝗿 & 𝗣𝗵𝗼𝘁𝗼 𝗠𝗮𝗸𝗲𝗿**\n"
            "   ▸ Photo par reply karke `/sticker` likhein\n"
            "   ▸ Sticker par reply karke `/photo` likhein\n\n"
            "📝 **𝟲. 𝗟𝘆𝗿𝗶𝗰𝘀 & 𝗤𝗥 𝗖𝗼𝗱𝗲**\n"
            "   ▸ `/lyrics <song name>` — Poore lyrics ke liye\n"
            "   ▸ `/qr <link ya text>` — HD QR code ke liye",
            reply_markup=back_kb
        )
    elif action == "sub":
        await cb.message.edit_text(
            "🎬 **𝗔𝗜 𝗩𝗜𝗗𝗘𝗢 𝗦𝗨𝗕𝗧𝗜𝗧𝗟𝗘𝗦 & 𝗧𝗥𝗔𝗡𝗦𝗟𝗔𝗧𝗢𝗥**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ **Step 1:** Koi bhi video chat mein bhejein.\n"
            "▸ **Step 2:** Us video par **Reply** karke `/sub` likhein.\n"
            "▸ **Step 3:** **English, Hindi, ya Hinglish** chunein — AI video ke andar stylish subtitles laga dega!",
            reply_markup=back_kb
        )
    elif action == "dl":
        await cb.message.edit_text(
            "📥 **𝗩𝗜𝗗𝗘𝗢 & 𝗔𝗨𝗗𝗜𝗢 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗘𝗥**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ **Step 1:** YouTube, Instagram Reels, Facebook ya X ka link seedha chat mein bhejein.\n"
            "▸ **Step 2:** Apni pasand ki quality (**1080p, 720p, 480p, 360p**) ya **Audio (MP3)** chunein.\n"
            "▸ **Step 3:** Bot turant download karke bhej dega!",
            reply_markup=back_kb
        )
    elif action == "mp3":
        await cb.message.edit_text(
            "🎵 **𝗩𝗜𝗗𝗘𝗢 𝗧𝗢 𝗠𝗣𝟯 𝗖𝗢𝗡𝗩𝗘𝗥𝗧𝗘𝗥**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ **Step 1:** Koi bhi video chat mein bhejein.\n"
            "▸ **Step 2:** Us video par **Reply** karke `/mp3` likh dein.\n"
            "▸ **Step 3:** Bot turant high-quality MP3 audio bana kar dega!",
            reply_markup=back_kb
        )
    elif action == "lyrics":
        await cb.message.edit_text(
            "📝 **𝗜𝗡𝗦𝗧𝗔𝗡𝗧 𝗦𝗢𝗡𝗚 𝗟𝗬𝗥𝗜𝗖𝗦**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ Chat mein `/lyrics` likh kar gaane ka naam likhein.\n"
            "▸ **Example:** `/lyrics Kesariya`\n"
            "▸ Bot turant poore lyrics bhej dega!",
            reply_markup=back_kb
        )
    elif action == "stk":
        await cb.message.edit_text(
            "🖼️ **𝗦𝗧𝗜𝗖𝗞𝗘𝗥 & 𝗣𝗛𝗢𝗧𝗢 𝗠𝗔𝗞𝗘𝗥**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ **Photo ➔ Sticker:** Kisi bhi photo par reply karke `/sticker` likhein.\n"
            "▸ **Sticker ➔ Photo:** Kisi bhi static sticker par reply karke `/photo` likhein.",
            reply_markup=back_kb
        )
    elif action == "qr":
        await cb.message.edit_text(
            "🔲 **𝗜𝗡𝗦𝗧𝗔𝗡𝗧 𝗤𝗥 𝗖𝗢𝗗𝗘 𝗠𝗔𝗞𝗘𝗥**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ `/qr` likh kar uske aage koi bhi link ya text likhein.\n"
            "▸ **Example:** `/qr https://google.com`\n"
            "▸ Bot turant HD QR Code bana kar bhej dega!",
            reply_markup=back_kb
        )
    elif action == "music":
        await cb.message.edit_text(
            "🎧 **𝗚𝗥𝗢𝗨𝗣 𝗩𝗖 𝗠𝗨𝗦𝗜𝗖 & 𝗩𝗜𝗗𝗘𝗢 𝗦𝗧𝗥𝗘𝗔𝗠**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "▸ **Audio Play:** `/play <gaane ka naam>`\n"
            "▸ **Video Play:** `/vplay <video ka naam>`\n"
            "▸ **Direct GC Media:** Group mein bheji gayi kisi bhi video/audio par reply karke `/play` ya `/vplay` likhein.\n"
            "▸ **Controls:** `/skip` • `/pause` • `/resume` • `/stop`",
            reply_markup=back_kb
        )
