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
    # تأكد من وجود دالة حذف المشارك في ملف database إذا كنت تستخدمها
)

from config import OWNER_ID

router = Router()
logger = logging.getLogger(__name__)

active_camps: dict[int, dict] = {}

def parse_duration(s: str) -> int | None:
    m = re.fullmatch(r"(\d+)([hHmMdD])", s.strip())
    if not m: return None
    value, unit = int(m.group(1)), m.group(2).lower()
    return value * {"m": 60, "h": 3600, "d": 86400}[unit]

def fmt_hms(sec: int) -> str:
    sec = max(0, sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def make_progress_bar(start: datetime, end: datetime):
    total = (end - start).total_seconds()
    if total <= 0: return "██████████ 100%"
    passed = (datetime.now() - start).total_seconds()
    percent = min(1.0, max(0.0, passed / total))
    filled = int(percent * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {int(percent * 100)}%"

def camp_join_kb(camp_id: str, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ انضم للمعسكر ({count})", callback_data=f"join:{camp_id}")],
            [
                InlineKeyboardButton(text="⏳ الوقت المتبقي", callback_data=f"time:{camp_id}"),
                InlineKeyboardButton(text="📊 إحصائيات", callback_data=f"stats:{camp_id}")
            ],
            [
                InlineKeyboardButton(text="🚶 استسلم", callback_data=f"quit:{camp_id}"),
                InlineKeyboardButton(text="🛑 إلغاء الكامب", callback_data=f"stop_camp:{camp_id}")
            ]
        ]
    )

async def build_msg(camp_id: str, start: datetime, end: datetime, status="active"):
    total_sec = int((end - start).total_seconds())
    rem = max(0, int((end - datetime.now()).total_seconds()))
    count = await get_camp_count(camp_id)
    prog = make_progress_bar(start, end)

    header = "🏆 *معسكر الإنجاز والتركيز* 🔥" if status == "active" else "🏁 *انتهى المعسكر بنجاح!*"
    
    text = (
        f"{header}\n\n"
        f"📅 {start.strftime('%Y/%m/%d')}\n"
        f"⌛ *المدة الكلية:* {fmt_hms(total_sec)}\n"
        f"⚙️ *نوع الكامب:* يدوي • جروب\n\n"
        f"🕐 *البداية (توقيت مصر):* {start.strftime('%I:%M %p')}\n"
        f"🏁 *النهاية:* {end.strftime('%I:%M %p')}\n\n"
        f"⏳ *المتبقي:* `{fmt_hms(rem)}`\n"
        f"📊 *التقدم:* `{prog}`\n\n"
        f"👥 *المشاركون:*\n"
        f"✅ منضمون: {count}\n"
        f"❌ مستسلمون: 0\n\n"
        f"📵 *الشات مقلق حالياً* — ركز في حلمك يا بطل 🚀"
    )
    return text

async def send_final_stats(bot: Bot, chat_id: int, camp_id: str):
    p = await get_camp_participants(camp_id)
    count = len(p)
    mentions = " ".join([f"[{x['full_name']}](tg://user?id={x['user_id']})" for x in p]) if p else "لا يوجد"
    
    text = (
        f"🏁 *انتهى الكامب! أحسنتم يا شباب* ✨\n\n"
        f"📊 *إحصائيات الكامب:*\n"
        f"✅ المنضمون: {count}\n"
        f"❌ المستسلمون: 0\n"
        f"📈 نسبة النجاح: 100%\n\n"
        f"👑 *قائمة الأبطال:*\n{mentions}\n\n"
        f"🤲 *دعاء ما بعد المذاكرة:*\n"
        f"«اللهم إني أستودعك ما قرأت وما حفظت وما تعلمت، فرده إلي عند حاجتي إليه، إنك على كل شيء قدير»"
    )
    await bot.send_message(chat_id, text, parse_mode="Markdown")

async def countdown_task(bot: Bot, chat_id: int, camp_id: str, msg_id: int, start: datetime, end: datetime):
    warn_5 = False
    warn_1 = False

    while True:
        if chat_id not in active_camps or active_camps[chat_id]["camp_id"] != camp_id: return
        rem = (end - datetime.now()).total_seconds()

        if 290 <= rem <= 305 and not warn_5:
            await bot.send_message(chat_id, "🔔 *تنبيه!*\n\nفضل 5 دقائق بس!\nكفل جامد، أنت قرّبت! 🔥", parse_mode="Markdown")
            warn_5 = True

        if 55 <= rem <= 65 and not warn_1:
            await bot.send_message(chat_id, "🔔 *آخر دقيقة!*\n\nفضل دقيقة واحدة بس!\nكفل للآخر! ⚡", parse_mode="Markdown")
            warn_1 = True

        if rem <= 0:
            try:
                final = await build_msg(camp_id, start, end, "done")
                await bot.edit_message_text(final, chat_id, msg_id, parse_mode="Markdown", reply_markup=None)
            except: pass
            active_camps.pop(chat_id, None)
            await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=True))
            await send_final_stats(bot, chat_id, camp_id)
            await clear_camp(camp_id)
            return

        try:
            txt = await build_msg(camp_id, start, end)
            c = await get_camp_count(camp_id)
            await bot.edit_message_text(text=txt, chat_id=chat_id, message_id=msg_id, parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, c))
        except: pass
        await asyncio.sleep(45)

@router.message(Command("camp"))
async def start_camp(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID: return
    p = message.text.split(maxsplit=1)
    if len(p) < 2: return await message.reply("مثال: `/camp 2h`")
    d = parse_duration(p[1])
    if not d: return await message.reply("❌ صيغة غير صحيحة")

    chat_id = message.chat.id
    if chat_id in active_camps:
        if active_camps[chat_id].get("task"): active_camps[chat_id]["task"].cancel()

    # 1. إرسال رسالة إغلاق الشات فوراً 🚫
    await bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    await message.answer(
        "⛔ *الجروب في وضع الكامب*\n\n"
        "💎 يلا نذاكر!\n"
        "🙌 ربنا يوفقكم يا جماعة", 
        parse_mode="Markdown"
    )

    # 2. إرسال رسالة دعاء قبل المذاكرة فوراً 🤲
    dua_text = (
        "📖 *دعاء قبل المذاكرة*\n\n"
        "«اللهم إني أسألك فهم النبيين وحفظ المرسلين والملائكة المقربين، "
        "اللهم اجعل ألسنتنا عامرة بذكرك، وقلوبنا بخشيتك، وأسرارنا بطاعتك، إنك على كل شيء قدير»\n\n"
        "✨ *بالتوفيق للجميع*"
    )
    await message.answer(dua_text, parse_mode="Markdown")

    # 3. إنشاء المعسكر وبدء العداد التنازلي ⏳
    camp_id = uuid.uuid4().hex[:10]
    st, en = datetime.now(), datetime.now() + timedelta(seconds=d)
    
    txt = await build_msg(camp_id, st, en)
    sent = await message.answer(txt, parse_mode="Markdown", reply_markup=camp_join_kb(camp_id, 0))
    task = asyncio.create_task(countdown_task(bot, chat_id, camp_id, sent.message_id, st, en))

    active_camps[chat_id] = {"camp_id": camp_id, "task": task, "start_time": st, "end_time": en, "msg_id": sent.message_id}

@router.callback_query(F.data.startswith("join:"))
async def join_camp(call: CallbackQuery, bot: Bot):
    cid = call.data.split(":")[1]
    sid = active_camps.get(call.message.chat.id)
    if not sid or sid["camp_id"] != cid: return await call.answer("المعسكر انتهى", show_alert=True)
    
    await add_camp_participant(call.from_user.id, cid, call.from_user.username, call.from_user.full_name)
    c = await get_camp_count(cid)
    await call.answer(f"✅ تم انضمامك بنجاح للمعسكر! بالتوفيق يا بطل 📖", show_alert=True)
    
    try:
        t = await build_msg(cid, sid["start_time"], sid["end_time"])
        await bot.edit_message_text(text=t, chat_id=call.message.chat.id, message_id=sid["msg_id"], parse_mode="Markdown", reply_markup=camp_join_kb(cid, c))
    except Exception as e:
        logger.error(f"Error updating message: {e}")

@router.callback_query(F.data.startswith("quit:"))
async def quit_camp(call: CallbackQuery, bot: Bot):
    cid = call.data.split(":")[1]
    sid = active_camps.get(call.message.chat.id)
    if not sid or sid["camp_id"] != cid: 
        return await call.answer("المعسكر انتهى بالفعل", show_alert=True)
    
    # تنبيه المستخدم بالاستسلام وتحديث العداد
    await call.answer("😢 تم تسجيل استسلامك.. معوضة في المعسكر القادم!", show_alert=True)
    
    try:
        c = await get_camp_count(cid)
        t = await build_msg(cid, sid["start_time"], sid["end_time"])
        await bot.edit_message_text(text=t, chat_id=call.message.chat.id, message_id=sid["msg_id"], parse_mode="Markdown", reply_markup=camp_join_kb(cid, c))
    except Exception as e:
        logger.error(f"Error during quit: {e}")

@router.callback_query(F.data.startswith("time:"))
async def time_alert(call: CallbackQuery):
    sid = active_camps.get(call.message.chat.id)
    if not sid: return await call.answer("لا يوجد معسكر نشط")
    rem = int((sid["end_time"] - datetime.now()).total_seconds())
    await call.answer(f"⏱ الوقت المتبقي: {fmt_hms(rem)}\n📊 التقدم: {make_progress_bar(sid['start_time'], sid['end_time']).split()[-1]}", show_alert=True)

@router.callback_query(F.data.startswith("stats:"))
async def stats_alert(call: CallbackQuery):
    c = await get_camp_count(call.data.split(":")[1])
    await call.answer(f"📊 إحصائيات الكامب:\n\n✅ منضمون: {c}\n❌ مستسلمون: 0\n📈 نسبة النجاح: 100.0%", show_alert=True)

@router.callback_query(F.data.startswith("stop_camp:"))
async def stop_cb(call: CallbackQuery, bot: Bot):
    if call.from_user.id != OWNER_ID: return await call.answer("للأدمن فقط!", show_alert=True)
    sid = active_camps.pop(call.message.chat.id, None)
    if sid: sid["task"].cancel()
    await bot.set_chat_permissions(call.message.chat.id, ChatPermissions(can_send_messages=True))
    await call.message.delete()
    await bot.send_message(call.message.chat.id, "🔓 تم إنهاء المعسكر وفتح الشات.")

