import asyncio
import re
import uuid
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatPermissions
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from database import (
    add_camp_participant, get_camp_participants,
    get_camp_count, clear_camp, get_setting, get_many_settings,
)
from keyboards.menus import camp_join_kb
from config import OWNER_ID

router = Router()
logger = logging.getLogger(__name__)

active_camps: dict[int, dict] = {}


def parse_duration(s: str) -> int | None:
    m = re.fullmatch(r"(\d+)([hHmMdD])", s.strip())
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2).lower()
    return v * {"m": 60, "h": 3600, "d": 86400}[u]


def fmt_hms(sec: int) -> str:
    sec = max(0, sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# 📊 دالة إنشاء شريط التحميل الاحترافي بالظبط مثل الصورة
def make_progress_bar(start: datetime, end: datetime) -> str:
    total = (end - start).total_seconds()
    if total <= 0:
        return "██████████ 100%"
    passed = (datetime.now() - start).total_seconds()
    pct = min(1.0, max(0.0, passed / total))
    blocks = int(pct * 10)
    bar = "█" * blocks + "░" * (10 - blocks)
    return f"{bar} {int(pct * 100)}%"


async def build_msg(camp_id: str, start: datetime, end: datetime) -> str:
    s = await get_many_settings("camp_dua", "camp_lock_msg")
    dua = s["camp_dua"] or "🤲 «رَبِّ زِدْنِي عِلْمًا وَارْزُقْنِي فَهْمًا»"
    
    # 📝 تنسيق الرسالة الجديد لمطابقة الصورةimage_47.png تماماً
    template = s["camp_lock_msg"] or (
        "👑 *Orino-Camp* 💎 دراسي عام\n\n"
        "📅 {date_long} · 📣 يدوري · ⛺ جروب\n"
        "⌛ *المدة الكلية:* {total_duration}\n\n"
        "📊 *الأوقات (توقيت مصر):*\n"
        "🏁 بداية: {start}\n"
        "🕗 نهاية: {end}\n\n"
        "⏱ *المتبقي:* {countdown}\n"
        "📊 *التقدم:* {progress}\n\n"
        "👥 *المشاركون:*\n"
        "✅ منضمون: {count}\n\n"
        "━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━\n"
        "🌟 *اللهم اجعلنا من أهل العلم والنجاح* 🌟"
    )
    
    total_seconds = int((end - start).total_seconds())
    remaining = max(0, int((end - datetime.now()).total_seconds()))
    count = await get_camp_count(camp_id)
    body = template.format(
        date_long=start.strftime("%Y/%m/%d"),
        total_duration=fmt_hms(total_seconds),
        countdown=fmt_hms(remaining),
        start=start.strftime("%I:%M %p"),
        end=end.strftime("%I:%M %p"),
        count=count,
        progress=make_progress_bar(start, end),
    )
    return f"{dua}\n━━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━ـ━\n{body}"


async def lock_chat(bot: Bot, chat_id: int):
    await bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=False),
    )


async def unlock_chat(bot: Bot, chat_id: int):
    await bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=True),
    )


def make_mention(p: dict) -> str:
    name = (p["full_name"] or p["username"] or "بطل").strip() or "بطل"
    return f"[{name}](tg://user?id={p['user_id']})"


async def send_final_message(bot: Bot, chat_id: int, camp_id: str):
    participants = await get_camp_participants(camp_id)
    template = await get_setting("camp_end_msg")
    if not template:
        template = (
            "🏆 *انتهى المعسكر بنجاح!* 🏆\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👑 *عاش يا أبطال المعسكر فوراً!* 🔥\n\n"
            "{mentions}\n\n"
            "💬 *طمنونا عملتوا إيه؟ شاركونا إنجازاتكم!* 🎊\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 *ربنا يكرمكم ويوفقكم في امتحاناتكم!* 🤲"
        )

    if not participants:
        text = template.replace("{mentions}", "_(لم ينضم أحد للمعسكر)_")
    else:
        mentions = " ".join(make_mention(p) for p in participants)
        text = template.replace("{mentions}", mentions)

    await bot.send_message(chat_id, text, parse_mode="Markdown")


async def countdown_task(
    bot: Bot, chat_id: int, camp_id: str,
    msg_id: int, start: datetime, end: datetime
):
    while True:
        if chat_id not in active_camps or active_camps[chat_id]["camp_id"] != camp_id:
            return

        remaining = (end - datetime.now()).total_seconds()
        if remaining <= 0:
            active_camps.pop(chat_id, None)
            await unlock_chat(bot, chat_id)
            await send_final_message(bot, chat_id, camp_id)
            await clear_camp(camp_id)
            return

        try:
            text = await build_msg(camp_id, start, end)
            count = await get_camp_count(camp_id)
            kb = camp_join_kb(camp_id)
            await bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=msg_id,
                parse_mode="Markdown",
                reply_markup=kb,
            )
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            continue
        except TelegramBadRequest:
            pass
        except Exception as e:
            logger.warning(f"countdown edit error: {e}")

        await asyncio.sleep(30) # التحديث الآمن كل 30 ثانية لحماية البوت


@router.message(Command("camp"))
async def start_camp(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID:
        try:
            await message.delete()
        except Exception:
            pass
        return

    if message.chat.type not in ("group", "supergroup"):
        await message.answer("⚠️ الأمر ده بيشتغل في الجروب بس!")
        return

    camp_chat = await get_setting("camp_chat_id")
    if camp_chat and str(message.chat.id) != camp_chat:
        try:
            await message.delete()
        except Exception:
            pass
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "⚠️ *الصيغة:* `/camp 4h` أو `/camp 30m` أو `/camp 1d`",
            parse_mode="Markdown",
        )
        return

    duration = parse_duration(parts[Parts[1]])
    if not duration:
        await message.reply(
            "❌ *صيغة غلط!* مثال: `/camp 4h`", parse_mode="Markdown"
        )
        return

    chat_id = message.chat.id
    if chat_id in active_camps:
        old = active_camps.pop(chat_id)
        t = old.get("task")
        if t:
            t.cancel()

    camp_id = uuid.uuid4().hex[:10]
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration)

    await lock_chat(bot, chat_id)

    text = await build_msg(camp_id, start_time, end_time)
    sent = await message.answer(
        text, parse_mode="Markdown", reply_markup=camp_join_kb(camp_id)
    )

    task = asyncio.create_task(
        countdown_task(bot, chat_id, camp_id, sent.message_id, start_time, end_time)
    )
    active_camps[chat_id] = {
        "camp_id": camp_id,
        "start_time": start_time,
        "end_time": end_time,
        "task": task,
        "msg_id": sent.message_id,
    }
    logger.info(f"[{chat_id}] 🔒 معسكر بدأ — {camp_id}")


@router.message(Command("stop"))
async def stop_camp(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID:
        try:
            await message.delete()
        except Exception:
            pass
        return

    chat_id = message.chat.id
    session = active_camps.pop(chat_id, None)
    if session:
        t = session.get("task")
        if t:
            t.cancel()
        await clear_camp(session["camp_id"])

    await unlock_chat(bot, chat_id)
    text = await get_setting("camp_stopped_msg") or (
        "🔓 *تم إيقاف المعسكر يدوياً!*\n\n"
        "💬 *الشات مفتوح للجميع دلوقتي* 🎊"
    )
    await message.answer(text, parse_mode="Markdown")
    logger.info(f"[{chat_id}] 🔓 معسكر أُوقف يدوياً")


@router.callback_query(F.data.startswith("join:"))
async def join_camp(call: CallbackQuery):
    camp_id = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    if chat_id not in active_camps or active_camps[chat_id]["camp_id"] != camp_id:
        await call.answer("⚠️ هذا المعسكر انتهى أو غير موجود.", show_alert=True)
        return

    await add_camp_participant(
        call.from_user.id, camp_id,
        call.from_user.username,
        call.from_user.full_name,
    )
    count = await get_camp_count(camp_id)
    await call.answer(f"✅ انضممت للمعسكر! أنت رقم {count} 🌟", show_alert=True)


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def guard_messages(message: Message, bot: Bot):
    if not message.from_user:
        return
    session = active_camps.get(message.chat.id)
    if not session:
        return
    if message.from_user.id == OWNER_ID:
        return
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.warning(f"delete error: {e}")

