import os, re, json, time, random, shutil, asyncio, urllib.parse, urllib.request, subprocess
import edge_tts
from PIL import Image
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery
from anony import app, config

USER_STATE = {}

VOICES = [
    ("hi_m", "🇮🇳 Hindi Male (Madhur)", "hi-IN-MadhurNeural"),
    ("hi_f", "🇮🇳 Hindi Female (Swara)", "hi-IN-SwaraNeural"),
    ("en_m", "🇬🇧 English Male (Chris)", "en-US-ChristopherNeural"),
    ("en_f", "🇬🇧 English Female (Jenny)", "en-US-JennyNeural"),
    ("ta_m", "🇮🇳 Tamil (Valluvar)", "ta-IN-ValluvarNeural"),
    ("te_m", "🇮🇳 Telugu (Mohan)", "te-IN-MohanNeural"),
    ("bn_m", "🇮🇳 Bengali (Bashkar)", "bn-IN-BashkarNeural"),
    ("mr_m", "🇮🇳 Marathi (Manohar)", "mr-IN-ManoharNeural"),
    ("gu_m", "🇮🇳 Gujarati (Niranjan)", "gu-IN-NiranjanNeural"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,application/json,*/*;q=0.8",
    "Referer": "https://pollinations.ai/"
}

def _build_3d_prompt(scene: str, topic: str) -> str:
    low = (scene + " " + topic).lower()
    if any(k in low for k in ["sheru", "lion", "mafia", "boss", "don", "bhai", "aukaat", "gangster"]):
        return (
            f"hyper-realistic 3D Pixar CGI animated movie still, anthropomorphic muscular white lion mafia boss "
            f"wearing crisp white tailored suit, black sunglasses, heavy gold chains, luxury golden mansion and supercars, "
            f"{scene}, Unreal Engine 5 photorealistic fur and skin texture, dramatic cinematic lighting, 8k"
        )
    return (
        f"hyper-realistic 3D Pixar Disney CGI animated movie scene, photorealistic textures, "
        f"dramatic volumetric cinematic lighting, expressive characters, {scene}, Unreal Engine 5, 8k"
    )

def _generate_4_scenes(topic: str, lang_key: str) -> list:
    lang_name = "English" if lang_key.startswith("en") else "Hindi/Hinglish"
    try:
        q = urllib.parse.quote(
            f"Write a viral 4-scene hyper-realistic 3D animated short story in {lang_name} on: {topic}. "
            "Return ONLY a JSON array of 4 objects with keys: "
            "\"narration\" (15-22 words punchy dramatic voiceover) and "
            "\"visual\" (short 6-10 word English visual description of the 3D scene)."
        )
        req = urllib.request.Request(f"https://text.pollinations.ai/{q}", headers=HEADERS)
        raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            arr = json.loads(m.group(0))
            if isinstance(arr, list) and len(arr) >= 3:
                return [
                    {
                        "narration": str(x["narration"]),
                        "short_q": str(x.get("visual", topic)),
                        "full_p": _build_3d_prompt(str(x.get("visual", topic)), topic)
                    }
                    for x in arr[:4]
                ]
    except Exception:
        pass

    t = topic.strip().rstrip(".")
    low = t.lower()
    if any(k in low for k in ["sheru", "lion", "mafia", "boss", "don", "bhai", "aukaat", "gangster"]):
        if lang_key.startswith("en"):
            raw_scenes = [
                ("Everyone knew the name of Sheru Bhai, the undisputed king who ruled the entire city!", "white lion mafia boss in white suit walking luxury mansion 3D render"),
                ("With a royal white suit, diamond chains, and fearless attitude, nobody dared to cross him.", "white lion in white suit with gorilla bodyguard in black suit 3D CGI"),
                ("When rivals tried to challenge his throne, he showed them what real power looks like!", "white lion boss in white suit luxury supercar showroom 3D animation"),
                ("Remember, true kings never follow rules — they create their own empire!", "majestic white lion king in white suit sunglasses golden palace 3D")
            ]
        else:
            raw_scenes = [
                ("Sheru Bhai ki ameeron wali aukaat dekh kar poore shehar ke dushmano ki neend ud gayi thi!", "white lion mafia boss in white suit walking luxury mansion 3D render"),
                ("Safed suit, gale mein sone ki moti chain, aur saath mein wafadar gorilla aur tiger bodyguards!", "white lion in white suit with gorilla bodyguard in black suit 3D CGI"),
                ("Jab dushmano ne saamne aane ki himmat ki, toh Sheru Bhai ne ek hi ishaare mein baazi palat di!", "white lion boss in white suit luxury supercar showroom 3D animation"),
                ("Asli badshah wahi hota hai jiski entry par poori duniya salaam thoke!", "majestic white lion king in white suit sunglasses golden palace 3D")
            ]
    else:
        if lang_key.startswith("en"):
            raw_scenes = [
                (f"This is the unforgettable story of {t} that will completely blow your mind!", f"{t} cinematic 3D Pixar realistic scene"),
                ("At first everyone doubted the journey, but true courage never backs down.", f"{t} dramatic dark night cinematic 3D animation"),
                ("Through relentless focus and power, every obstacle turned into a massive victory!", f"{t} epic action golden lighting 3D CGI render"),
                ("Remember, when your mindset is unstoppable, the entire world salutes you!", f"{t} victorious golden sunrise skyline 3D render")
            ]
        else:
            raw_scenes = [
                (f"Yeh kahani hai {t} ki, jo aapki soch ko poori tarah badal kar rakh degi!", f"{t} cinematic 3D Pixar realistic scene"),
                ("Shuruat mein har kisi ne kaha ki yeh namumkin hai, lekin usne kabhi haar nahi maani.", f"{t} dramatic dark night cinematic 3D animation"),
                ("Din raat ki mehnat aur junoon ne aakhirkar kismat ko bhi jhukne par majboor kar diya!", f"{t} epic action golden lighting 3D CGI render"),
                ("Yaad rakho, jab irada pakka ho toh poori duniya salaam thokti hai!", f"{t} victorious golden sunrise skyline 3D render")
            ]
    return [{"narration": n, "short_q": q, "full_p": _build_3d_prompt(q, t)} for n, q in raw_scenes]

def _save_valid_image(raw_bytes: bytes, out_img: str) -> bool:
    if not raw_bytes or len(raw_bytes) < 8000:
        return False
    tmp = out_img + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw_bytes)
    try:
        im = Image.open(tmp).convert("RGB")
        if im.width < 200 or im.height < 200:
            os.remove(tmp)
            return False
        im.save(out_img, "JPEG", quality=94)
        os.remove(tmp)
        return True
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        return False

def _fetch_photoreal_3d_image(scene_obj: dict, idx: int, out_img: str):
    short_q = scene_obj["short_q"]
    queries = [
        f"{short_q} 3D CGI render",
        f"{short_q} Pixar 3D animation art",
        "3D Pixar CGI lion in suit luxury mafia art",
        "3D CGI animal character suit cinematic render"
    ]
    for q in queries:
        try:
            enc = urllib.parse.quote(q)
            bing_url = f"https://www.bing.com/images/async?q={enc}&first=0&count=15&qft=+filterui:aspect-tall"
            req = urllib.request.Request(bing_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
            urls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", html)
            if not urls:
                urls = re.findall(r'"murl":"(https?://[^"]+?)"', html)
            random.shuffle(urls)
            for u in urls[:12]:
                try:
                    ireq = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bing.com/"})
                    idata = urllib.request.urlopen(ireq, timeout=8).read()
                    if _save_valid_image(idata, out_img):
                        return
                except Exception:
                    continue
        except Exception:
            continue
    raise RuntimeError("No image returned — please retry.")

async def _tts(text: str, voice_id: str, out_mp3: str):
    comm = edge_tts.Communicate(text, voice_id, rate="+5%")
    await comm.save(out_mp3)

def _dur(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ]).decode().strip()
    return max(float(out), 2.0)

def _wrap_caption(text: str, width: int = 25) -> str:
    words, lines, cur = text.split(), [], []
    for w in words:
        if sum(len(x) for x in cur) + len(w) + len(cur) <= width:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines[:3]).replace(":", " ").replace("'", "")

def _render_animated_clip(img_p: str, aud_p: str, narr: str, idx: int, clip_p: str):
    d = _dur(aud_p)
    frames = int(d * 25) + 5
    txt_p = clip_p + ".txt"
    with open(txt_p, "w", encoding="utf-8") as f:
        f.write(_wrap_caption(narr))

    if idx % 2 == 1:
        zp = f"zoompan=z='min(zoom+0.0018,1.20)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25"
    else:
        zp = f"zoompan=z='1.16-0.0012*on':d={frames}:x='iw/2-(iw/zoom/2)+sin(on/14)*20':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25"

    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{zp},"
        f"eq=contrast=1.08:saturation=1.18,"
        f"drawbox=x=28:y=950:w=664:h=215:color=black@0.65:t=fill,"
        f"drawtext=textfile={txt_p}:fontcolor=yellow:fontsize=35:line_spacing=10:borderw=2:bordercolor=black:x=(w-text_w)/2:y=982"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", img_p, "-i", aud_p,
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", clip_p
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _concat(clips: list, out_mp4: str):
    lst = out_mp4 + ".list"
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out_mp4
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def run_photoreal_story_pipeline(m: Message, scenes: list, voice_idx: int, topic_label: str):
    work = f"/tmp/pr3d_{m.chat.id}_{m.id}"
    os.makedirs(work, exist_ok=True)
    _, v_label, v_id = VOICES[voice_idx % len(VOICES)]
    st = await m.reply_text(
        f"🎬 <b>Creating Hyper-Realistic 3D Animated Story...</b>\n"
        f"🎙 <b>Voice:</b> {v_label}\n"
        "⏳ <i>Generating 4 photorealistic 3D visuals, neural voiceover & motion (~15–25s)...</i>"
    )
    clips = []
    try:
        for i, sc in enumerate(scenes, 1):
            narr = sc["narration"].strip()
            img_p = os.path.join(work, f"pr_{i}.jpg")
            aud_p = os.path.join(work, f"vx_{i}.mp3")
            clip_p = os.path.join(work, f"cl_{i}.mp4")

            await asyncio.gather(
                asyncio.to_thread(_fetch_photoreal_3d_image, sc, i, img_p),
                _tts(narr, v_id, aud_p)
            )
            await asyncio.to_thread(_render_animated_clip, img_p, aud_p, narr, i, clip_p)
            clips.append(clip_p)

        final_mp4 = os.path.join(work, "Wavy_Photoreal_3D_Story.mp4")
        await asyncio.to_thread(_concat, clips, final_mp4)
        script_summary = "\n".join([f"<b>{i}.</b> {s['narration']}" for i, s in enumerate(scenes, 1)])
        await st.edit_text("📤 <b>Uploading Hyper-Realistic 3D Story Video...</b>")
        await m.reply_video(
            final_mp4,
            caption=f"🎬 <b>AI Realistic 3D Story Video</b>\n━━━━━━━━━━━━━━━━━━━━━━\n<b>Topic:</b> {topic_label}\n<b>Voice:</b> {v_label}\n\n📝 <b>Script:</b>\n{script_summary}"
        )
        await st.delete()
    except Exception as e:
        await st.edit_text(f"❌ Error: <code>{e}</code>")
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _tg_post(method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=10).read()

def story_studio_kb(v_idx: int):
    _, v_label, _ = VOICES[v_idx % len(VOICES)]
    return {
        "inline_keyboard": [
            [{"text": "🤖 Auto AI Script + Realistic 3D Video", "callback_data": "st_mode_idea", "style": "primary"}],
            [{"text": "✍️ Use My Own Custom Script", "callback_data": "st_mode_custom", "style": "primary"}],
            [{"text": f"🎙 {v_label} (Tap to Switch)", "callback_data": "st_next_voice", "style": "success"}],
            [{"text": "🔙 Back to Features", "callback_data": "feat_menu", "style": "success"}]
        ]
    }

@app.on_message(filters.command(["story", "aivideo"]), group=-26)
async def story_cmd(_, m: Message):
    uid = m.from_user.id if m.from_user else 0
    state = USER_STATE.setdefault(uid, {"mode": None, "v_idx": 0})
    arg = m.text.split(None, 1)[1].strip() if len(m.command) > 1 else ""
    if arg:
        state["mode"] = None
        v_key = VOICES[state["v_idx"] % len(VOICES)][0]
        scenes = await asyncio.to_thread(_generate_4_scenes, arg, v_key)
        await run_photoreal_story_pipeline(m, scenes, state["v_idx"], arg[:45])
    else:
        await asyncio.to_thread(_tg_post, "sendMessage", {
            "chat_id": m.chat.id,
            "text": (
                "🎬 <b>AI Photorealistic 3D Story Studio</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Create viral <b>Hyper-Realistic 3D Animated Shorts / Reels</b> (like Sheru Bhai Mafia & 3D Animal Stories) with 9 Indian & English Voices!\n\n"
                "👇 <b>Choose an option below (or send <code>/story your idea</code>):</b>"
            ),
            "parse_mode": "HTML",
            "reply_markup": story_studio_kb(state["v_idx"])
        })
    m.stop_propagation()

@app.on_callback_query(filters.regex(r"^(wavy_story|st_mode_|st_next_voice)"), group=-26)
async def story_cb(_, cq: CallbackQuery):
    await cq.answer()
    uid = cq.from_user.id
    state = USER_STATE.setdefault(uid, {"mode": None, "v_idx": 0})
    base = {"chat_id": cq.message.chat.id, "message_id": cq.message.id, "parse_mode": "HTML"}

    if cq.data == "wavy_story":
        txt = (
            "🎬 <b>AI Photorealistic 3D Story Studio</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Create viral <b>Hyper-Realistic 3D Animated Shorts / Reels</b> with 9 Indian & English Voices and Viral Captions!\n\n"
            "👇 <b>Select your creation mode:</b>"
        )
        try:
            await asyncio.to_thread(_tg_post, "editMessageCaption", {**base, "caption": txt, "reply_markup": story_studio_kb(state["v_idx"])})
        except Exception:
            await asyncio.to_thread(_tg_post, "editMessageText", {**base, "text": txt, "reply_markup": story_studio_kb(state["v_idx"])})
    elif cq.data == "st_next_voice":
        state["v_idx"] = (state["v_idx"] + 1) % len(VOICES)
        await asyncio.to_thread(_tg_post, "editMessageReplyMarkup", {
            "chat_id": cq.message.chat.id,
            "message_id": cq.message.id,
            "reply_markup": story_studio_kb(state["v_idx"])
        })
    elif cq.data == "st_mode_idea":
        state["mode"] = "idea"
        await cq.message.reply_text("🤖 <b>Auto AI Script Mode Activated!</b>\nSend your story topic now (e.g. <i>Sheru Bhai mafia king entry</i> or <i>Emotional lion father and cub story</i>):")
    elif cq.data == "st_mode_custom":
        state["mode"] = "custom"
        await cq.message.reply_text("✍️ <b>Custom Script Mode Activated!</b>\nSend your script lines (separate scenes with new lines or full stops — max 5 lines):")
    cq.stop_propagation()

@app.on_message(filters.private & filters.text & ~filters.command(["start", "features", "help", "convert", "story", "aivideo", "play", "vplay", "dl", "sub", "mp3", "lyrics", "qr"]), group=-26)
async def story_input(_, m: Message):
    uid = m.from_user.id if m.from_user else 0
    state = USER_STATE.get(uid)
    if not state or not state.get("mode"):
        return
    if re.match(r"^https?://", m.text.strip()):
        return
    mode = state["mode"]
    state["mode"] = None
    txt = m.text.strip()
    v_key = VOICES[state["v_idx"] % len(VOICES)][0]

    if mode == "idea":
        scenes = await asyncio.to_thread(_generate_4_scenes, txt, v_key)
        await run_photoreal_story_pipeline(m, scenes, state["v_idx"], txt[:45])
    else:
        lines = [l.strip() for l in re.split(r"[\n।]+", txt) if len(l.strip()) > 3][:5]
        if not lines:
            return await m.reply_text("❌ Please send at least 1 valid sentence.")
        scenes = [{"narration": l, "short_q": f"{l} 3D CGI Pixar render", "full_p": _build_3d_prompt(l, txt)} for l in lines]
        await run_photoreal_story_pipeline(m, scenes, state["v_idx"], "Custom 3D Script")
    m.stop_propagation()
