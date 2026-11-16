import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from anony import app

async def _auto_del(msg: Message, delay: int = 45):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

@app.on_message(filters.group & filters.new_chat_members)
async def welcome_new_members(_, m: Message):
    adder = m.from_user
    chat_title = m.chat.title or "𝘁𝗵𝗶𝘀 𝗚𝗿𝗼𝘂𝗽"
    try:
        count = await app.get_chat_members_count(m.chat.id)
    except Exception:
        count = "—"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ 𝗘𝘅𝗽𝗹𝗼𝗿𝗲 𝗪𝗮𝘃𝘆 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀", callback_data="feat_menu")]
    ])

    for member in m.new_chat_members:
        if member.is_bot:
            continue

        is_invited = adder and adder.id != member.id
        invite_line = (
            f"▸ 🤝 **𝗜𝗻𝘃𝗶𝘁𝗲𝗱 𝗕𝘆 :** {adder.mention}\n"
            if is_invited
            else "▸ 🔗 **𝗝𝗼𝗶𝗻𝗲𝗱 𝗩𝗶𝗮 :** 𝖨𝗇𝗏𝗂𝗍𝖾 𝖫𝗂𝗇𝗄 / 𝖲𝖾𝖺𝗋𝖼𝗁\n"
        )

        text = (
            f"✦ **𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 {chat_title.upper()}** ✦\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 **𝗛𝗲𝘆** {member.mention}, 𝘄𝗲𝗹𝗰𝗼𝗺𝗲 𝗮𝗯𝗼𝗮𝗿𝗱!\n\n"
            f"▸ 🆔 **𝗨𝘀𝗲𝗿 𝗜𝗗 :** `{member.id}`\n"
            f"{invite_line}"
            f"▸ 👥 **𝗠𝗲𝗺𝗯𝗲𝗿𝘀 :** `{count}`\n\n"
            f"🎧 *Enjoy lag-free VC Music, Video & AI Tools!*"
        )
        sent = await m.reply_text(text, reply_markup=kb)
        asyncio.create_task(_auto_del(sent, 45))

@app.on_message(filters.group & filters.left_chat_member)
async def goodbye_member(_, m: Message):
    member = m.left_chat_member
    if not member or member.is_bot:
        return

    kicker = m.from_user
    if kicker and kicker.id != member.id:
        action_line = f"▸ ⚡ **𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗕𝘆 :** {kicker.mention}"
    else:
        action_line = "▸ 🚪 **𝗦𝘁𝗮𝘁𝘂𝘀 :** 𝖫𝖾𝖿𝗍 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉"

    text = (
        f"✦ **𝗚𝗢𝗢𝗗𝗕𝗬𝗘** ✦\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 {member.mention} 𝗵𝗮𝘀 𝗹𝗲𝗳𝘁 𝘁𝗵𝗲 𝗰𝗵𝗮𝘁.\n"
        f"{action_line}\n"
        f"▸ 🆔 **𝗨𝘀𝗲𝗿 𝗜𝗗 :** `{member.id}`"
    )
    sent = await m.reply_text(text)
    asyncio.create_task(_auto_del(sent, 35))
