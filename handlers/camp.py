import asyncio
import re
import uuid
import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ChatPermissions,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

from database import (
    add_camp_participant,
    get_camp_participants,
    get_camp_count,
    clear_camp,
    get_setting,
    get_many_settings,
)

from config import OWNER_ID

router = Router()
logger = logging.getLogger(__name__)

active_camps: dict[int, dict] = {}


def parse_duration(s: str) -> int | None:
    m = re.fullmatch(r"(\d+)([hHmMdD])", s.strip())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2).lower()
    return value * {
        "m": 60,
        "h": 3600,
        "d": 86400
    }[unit]


def fmt_hms(sec: int) -> str:
    sec = max(0, sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def make_progress_bar(start: datetime, end: datetime):
    total = (end - start).total_seconds()
    if total <= 0:
        return "██████████ 100%"
    passed = (datetime.now() - start).total_seconds()
    percent = min(1.0, max(0.0, passed / total))
    filled = int(percent * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {int(percent * 100)}%"


# ⌨️ دالة الأزرار المتطابقة مع الفيديو تماماً
def camp_join_kb(camp_id: str, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔥 انضم للمعسكر ({count})",
                    callback_data=f"join:{camp_id}"
                )
            ],
            [
                InlineKeyboardButton(text="⏳ الوقت المتبقي", callback_data=f"time:{camp_id}"),
                InlineKeyboardButton(text="📊 إحصائيات", callback_data=f"stats:{camp_id}")
            ],
            [
                InlineKeyboardButton(text="🛑 إلغاء الكامب", callback_data=f"stop_camp:{camp_id}")
            ]
        ]
    )


async def build_msg(camp_id: str, start: datetime, end: datetime):
    s = await get_many_settings("camp_dua")
    dua = s.get("camp_dua") or "🤲 «رَبِّ زِدْنِي عِلْمًا وَارْزُقْنِي فَهْمًا»"
    
    total_seconds = int((end - start).total_seconds())
    remaining = max(0, int((end - datetime.now()).total_seconds()))
    count = await get_camp_count(camp_id)
    progress = make_progress_bar(start, end)

    text = (
        f"{dua}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 *Orino Camp* 💎\n\n"
        f"📅 {start.strftime('%Y/%m/%d')}\n"
        f"⌛ *المدة:* {fmt_hms(total_seconds)}\n\n"
        f"🕐 *البداية:* {start.strftime('%I:%M %p')}\n"
        f"🏁 *النهاية:* {end.strftime('%I:%M %p')}\n\n"
        f"⏳ *المتبقي:*\n"
        f"`{fmt_hms(remaining)}`\n\n"
        f"📊 *التقدم:*\n"
        f"`{progress}`\n\n"
        f"👥 *المشاركون:* {count}\n\n"
        f"📵 *الشات مقفول حالياً*\n"
        f"ركز ومتفتحش تيك توك يا بطل 💀"
    )
    return text


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
    if not participants:
        text = "🏁 انتهى المعسكر ولم ينضم أحد."
    else:
        mentions = " ".join(make_mention(p) for p in participants)
        text = (
            "🏆 *انتهى المعسكر بنجاح!* 🔥\n\n"
            f"{mentions}\n\n"
            "عاش يا وحوش 💀"
        )
    await bot.send_message(chat_id, text, parse_mode="Markdown")


# 🔄 دالة التحديث الآمنة في الخلفية (كل 60 ثانية لمنع حظر البوت)
async def countdown_task(bot: Bot, chat_id: int, camp_id: str, msg_id: int, start: datetime, end: datetime):
    while True:
        if chat_id not in active_camps or active_camps[chat_id]["camp_id"] != camp_id:
            return

        remaining = (end - datetime.now()).total_seconds()
        
        # 🚨 إذا انتهى الوقت تلقائياً
        if remaining <= 0:
            try:
                count = await get_camp_count(camp_id)
                final_text = (
                    f"🤲 المعسكر انتهى واكتملت المهمة بنجاح!\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"👑 *Orino Camp* 💎\n\n"
                    f"📅 {start.strftime('%Y/%m/%d')}\n"
                    f"⌛ *المدة الكلية:* {fmt_hms(int((end - start).total_seconds()))}\n\n"
                    f"⏳ *المتبقي:* `00:00:00`\n"
                    f"📊 *التقدم:* `██████████ 100%`\n\n"
                    f"👥 *إجمالي الأبطال المشاركين:* {count}\n\n"
                    f"🔓 تم فتح الشات تلقائياً للجميع!"
                )
                await bot.edit_message_text(
                    text=final_text, chat_id=chat_id, message_id=msg_id,
                    parse_mode="Markdown", reply_markup=None
                )
            except Exception:
                pass

            active_camps.pop(chat_id, None)
            await unlock_chat(bot, chat_id)
            await send_final_message(bot, chat_id, camp_id)
            await clear_camp(camp_id)
            return

        try:
            text = await build_msg(camp_id, start, end)
            count = await get_camp_count(camp_id)
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id,
                parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, count)
            )
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            continue
        except TelegramBadRequest:
            pass
        except Exception as e:
            logger.warning(f"countdown background edit error: {e}")

        await asyncio.sleep(60)


@router.message(Command("camp"))
async def start_camp(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("مثال:\n`/camp 2h`", parse_mode="Markdown")
        return

    duration = parse_duration(parts[1])
    if not duration:
        await message.reply("❌ صيغة غلط", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    if chat_id in active_camps:
        old = active_camps.pop(chat_id)
        task = old.get("task")
        if task:
            task.cancel()

    camp_id = uuid.uuid4().hex[:10]
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration)

    await lock_chat(bot, chat_id)
    text = await build_msg(camp_id, start_time, end_time)
    sent = await message.answer(text, parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, 0))

    task = asyncio.create_task(countdown_task(bot, chat_id, camp_id, sent.message_id, start_time, end_time))

    # حفظ البيانات كاملة لاستخدامها في التحديثات اللحظية عند ضغط الأزرار
    active_camps[chat_id] = {
        "camp_id": camp_id,
        "task": task,
        "start_time": start_time,
        "end_time": end_time,
        "msg_id": sent.message_id
    }


@router.message(Command("stop"))
async def stop_camp(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID:
        return

    chat_id = message.chat.id
    session = active_camps.pop(chat_id, None)
    if session:
        task = session.get("task")
        if task:
            task.cancel()
        await clear_camp(session["camp_id"])

    await unlock_chat(bot, chat_id)
    await message.answer("🔓 تم إنهاء المعسكر")


# 📥 استقبال ضغطة زرار الانضمام وتحديث الرسالة فوراً
@router.callback_query(F.data.startswith("join:"))
async def join_camp(call: CallbackQuery, bot: Bot):
    camp_id = call.data.split(":")[1]
    chat_id = call.message.chat.id
    session = active_camps.get(chat_id)

    if not session or session["camp_id"] != camp_id:
        await call.answer("المعسكر انتهى", show_alert=True)
        return

    await add_camp_participant(
        call.from_user.id,
        camp_id,
        call.from_user.username,
        call.from_user.full_name,
    )
    count = await get_camp_count(camp_id)
    await call.answer(f"🔥 دخلت المعسكر\nأنت رقم {count}", show_alert=True)
    
    # ⚡ تحديث إجباري فوري للرسالة والعداد لتظهر الحركة فوراً
    try:
        text = await build_msg(camp_id, session["start_time"], session["end_time"])
        await bot.edit_message_text(
            text=text, chat_id=chat_id, message_id=session["msg_id"],
            parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, count)
        )
    except Exception:
        pass


# ⏳ استقبال ضغطة زرار الوقت المتبقي (يحدث الرسالة الكبيرة + يعطي الـ Alert)
@router.callback_query(F.data.startswith("time:"))
async def camp_time_alert(call: CallbackQuery, bot: Bot):
    camp_id = call.data.split(":")[1]
    chat_id = call.message.chat.id
    session = active_camps.get(chat_id)
    
    if not session or session["camp_id"] != camp_id:
        await call.answer("⚠️ المعسكر غير نشط حالياً.", show_alert=True)
        return
        
    remaining = (session["end_time"] - datetime.now()).total_seconds()
    progress = make_progress_bar(session["start_time"], session["end_time"])
    count = await get_camp_count(camp_id)
    
    # ⚡ تحديث فوري للرسالة الأساسية بالجروب عند الضغط
    try:
        text = await build_msg(camp_id, session["start_time"], session["end_time"])
        await bot.edit_message_text(
            text=text, chat_id=chat_id, message_id=session["msg_id"],
            parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, count)
        )
    except Exception:
        pass

    # إظهار التنبيه الفوقي المتطابق
    alert_text = (
        f"⛺ Orino Camp | Pro ⏱\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⏳ المتبقي: {fmt_hms(int(remaining))}\n"
        f"📊 التقدم: {progress.split()[-1]}"
    )
    await call.answer(alert_text, show_alert=True)


# 📊 استقبال ضغطة زرار الإحصائيات
@router.callback_query(F.data.startswith("stats:"))
async def camp_stats_alert(call: CallbackQuery):
    camp_id = call.data.split(":")[1]
    count = await get_camp_count(camp_id)
    alert_text = (
        f"⛺ Orino Camp | Pro 📊\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ الأبطال المستعدون: {count}\n"
        f"❌ المستسلمون: 0\n"
        f"📈 نسبة الحماس: 100%"
    )
    await call.answer(alert_text, show_alert=True)


# 🔴 استقبال ضغطة زرار إلغاء الكامب من الأدمن
@router.callback_query(F.data.startswith("stop_camp:"))
async def camp_stop_callback(call: CallbackQuery, bot: Bot):
    if call.from_user.id != OWNER_ID:
        await call.answer("❌ هذا الزر مخصص للأدمن فقط!", show_alert=True)
        return
    session = active_camps.pop(call.message.chat.id, None)
    if session and session.get("task"):
        session["task"].cancel()
        await clear_camp(session["camp_id"])
    await unlock_chat(bot, call.message.chat.id)
    await call.message.delete()
    await bot.send_message(call.message.chat.id, "🔓 تم إنهاء المعسكر بواسطة الأدمن.")


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

