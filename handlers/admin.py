import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_user_count, get_all_user_ids,
    get_setting, set_setting, reset_setting, get_many_settings,
)
from keyboards.menus import (
    admin_menu_kb, admin_plans_kb, admin_content_kb,
    admin_btns_kb, back_kb, cancel_kb,
)
from config import OWNER_ID

router = Router()
logger = logging.getLogger(__name__)


class AdminFSM(StatesGroup):
    broadcast    = State()
    set_channel  = State()
    set_camp_grp = State()
    plan_science = State()
    plan_math    = State()
    plan_azhar   = State()
    edit_about       = State()
    edit_welcome     = State()
    edit_owner       = State()
    edit_camp_info   = State()
    edit_btn_study   = State()
    edit_btn_ai      = State()
    edit_btn_camp    = State()
    edit_btn_about   = State()
    edit_dua         = State()
    edit_lock_msg    = State()
    edit_end_msg     = State()
    edit_stopped_msg = State()


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer(
        "🛠 *لوحة التحكم الأسطورية* 👑\n\nاختار العملية 👇",
        parse_mode="Markdown",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "back_admin")
async def back_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "🛠 *لوحة التحكم الأسطورية* 👑\n\nاختار العملية 👇",
        parse_mode="Markdown",
        reply_markup=admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "adm_stats")
async def cb_stats(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ مش مصرح لك!", show_alert=True)
        return
    s = await get_many_settings("force_channel", "camp_chat_id")
    total = await get_user_count()
    await call.message.edit_text(
        "📊 *إحصائيات المنظومة*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *إجمالي الطلاب:* `{total}`\n"
        f"📌 *قناة الاشتراك:* `{s['force_channel'] or 'غير محدد'}`\n"
        f"📍 *جروب المعسكر:* `{s['camp_chat_id'] or 'غير محدد'}`\n",
        parse_mode="Markdown",
        reply_markup=admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ مش مصرح لك!", show_alert=True)
        return
    await state.set_state(AdminFSM.broadcast)
    await call.message.edit_text(
        "📢 *إذاعة عامة*\n\n"
        "اكتب الرسالة اللي عاوز تبعتها لكل الطلاب:\n"
        "_(يدعم Markdown والإيموجيات)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(AdminFSM.broadcast)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    users = await get_all_user_ids()
    success = failed = 0
    status = await message.answer(f"⏳ جاري الإرسال لـ {len(users)} طالب...")
    for uid in users:
        try:
            await bot.send_message(uid, message.text, parse_mode="Markdown")
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(
        f"✅ *تمت الإذاعة!*\n\n📤 وصلت لـ: {success}\n❌ فشلت: {failed}",
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "adm_channel")
async def cb_set_channel(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    current = await get_setting("force_channel") or "غير محدد"
    await state.set_state(AdminFSM.set_channel)
    await call.message.edit_text(
        f"🔐 *تعديل قناة الاشتراك الإجباري*\n\n"
        f"الحالي: `{current}`\n\n"
        "اكتب معرّف القناة مثل `@mychannel`\n"
        "أو اكتب `clear` لإلغاء الاشتراك الإجباري.",
        parse_mode="Markdown", reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(AdminFSM.set_channel)
async def do_set_channel(message: Message, state: FSMContext):
    await state.clear()
    val = message.text.strip()
    if val.lower() == "clear":
        await set_setting("force_channel", "")
        await message.answer("✅ *تم إلغاء الاشتراك الإجباري!*",
                             parse_mode="Markdown", reply_markup=admin_menu_kb())
    else:
        ch = val if val.startswith("@") else f"@{val}"
        await set_setting("force_channel", ch)
        await message.answer(f"✅ *تم تعيين القناة:* `{ch}`",
                             parse_mode="Markdown", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_camp_group")
async def cb_set_camp_group(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    current = await get_setting("camp_chat_id") or "غير محدد"
    await state.set_state(AdminFSM.set_camp_grp)
    await call.message.edit_text(
        f"📍 *تعيين جروب المعسكرات*\n\n"
        f"الحالي: `{current}`\n\n"
        "اكتب Chat ID الجروب (رقم يبدأ بـ `-`)\n"
        "مثال: `-1001234567890`\n\n"
        "أو اكتب `clear` لإلغاء القيد.",
        parse_mode="Markdown", reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(AdminFSM.set_camp_grp)
async def do_set_camp_group(message: Message, state: FSMContext):
    await state.clear()
    val = message.text.strip()
    if val.lower() == "clear":
        await set_setting("camp_chat_id", "")
        await message.answer("✅ *تم إلغاء قيد الجروب!*",
                             parse_mode="Markdown", reply_markup=admin_menu_kb())
    else:
        await set_setting("camp_chat_id", val)
        await message.answer(f"✅ *تم تعيين جروب المعسكر:* `{val}`",
                             parse_mode="Markdown", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_plans_menu")
async def cb_plans_menu(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await call.message.edit_text(
        "📝 *تعديل الخطط الدراسية*\n\nاختار الشعبة 👇",
        parse_mode="Markdown", reply_markup=admin_plans_kb(),
    )
    await call.answer()


async def _ask_plan(call: CallbackQuery, state: FSMContext,
                    st: State, key: str, label: str):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cur = await get_setting(key)
    preview = (cur[:150] + "...") if len(cur) > 150 else (cur or "_(افتراضي)_")
    await state.set_state(st)
    await call.message.edit_text(
        f"📝 *تعديل خطة {label}*\n\n"
        f"الحالية (أول 150 حرف):\n`{preview}`\n\n"
        "اكتب الخطة الجديدة كاملة\n"
        "أو اكتب `reset` للرجوع للافتراضي.",
        parse_mode="Markdown", reply_markup=cancel_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "adm_plan_science")
async def cb_plan_science(call: CallbackQuery, state: FSMContext):
    await _ask_plan(call, state, AdminFSM.plan_science, "plan_science", "علمي علوم")


@router.callback_query(F.data == "adm_plan_math")
async def cb_plan_math(call: CallbackQuery, state: FSMContext):
    await _ask_plan(call, state, AdminFSM.plan_math, "plan_math", "علمي رياضة")


@router.callback_query(F.data == "adm_plan_azhar")
async def cb_plan_azhar(call: CallbackQuery, state: FSMContext):
    await _ask_plan(call, state, AdminFSM.plan_azhar, "plan_azhar", "القسم الأزهري")


async def _save_plan(message: Message, state: FSMContext, key: str, label: str):
    await state.clear()
    if message.text.strip().lower() == "reset":
        await reset_setting(key)
        await message.answer(f"✅ *تم إعادة خطة {label} للافتراضي!*",
                             parse_mode="Markdown", reply_markup=admin_plans_kb())
    else:
        await set_setting(key, message.text.strip())
        await message.answer(f"✅ *تم حفظ خطة {label}!*",
                             parse_mode="Markdown", reply_markup=admin_plans_kb())


@router.message(AdminFSM.plan_science)
async def save_plan_science(message: Message, state: FSMContext):
    await _save_plan(message, state, "plan_science", "علمي علوم")


@router.message(AdminFSM.plan_math)
async def save_plan_math(message: Message, state: FSMContext):
    await _save_plan(message, state, "plan_math", "علمي رياضة")


@router.message(AdminFSM.plan_azhar)
async def save_plan_azhar(message: Message, state: FSMContext):
    await _save_plan(message, state, "plan_azhar", "القسم الأزهري")


@router.callback_query(F.data == "adm_content_menu")
async def cb_content_menu(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await call.message.edit_text(
        "✏️ *تعديل محتوى البوت*\n\n"
        "كل حاجة في البوت قابلة للتعديل 👇",
        parse_mode="Markdown", reply_markup=admin_content_kb(),
    )
    await call.answer()


async def _ask_content(
    call: CallbackQuery, state: FSMContext,
    st: State, key: str, label: str, hint: str = ""
):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cur = await get_setting(key)
    preview = (cur[:200] + "...") if len(cur) > 200 else (cur or "_(افتراضي)_")
    await state.set_state(st)
    msg = (
        f"✏️ *تعديل: {label}*\n\n"
        f"الحالي:\n`{preview}`\n\n"
        f"{hint}\n"
        "اكتب القيمة الجديدة أو اكتب `reset` للقيمة الافتراضية."
    )
    await call.message.edit_text(msg, parse_mode="Markdown",
                                 reply_markup=cancel_kb("adm_content_menu"))
    await call.answer()


async def _save_content(
    message: Message, state: FSMContext,
    key: str, label: str, back_kb_fn
):
    await state.clear()
    val = message.text.strip()
    if val.lower() == "reset":
        await reset_setting(key)
        await message.answer(f"✅ *تم إعادة {label} للافتراضي!*",
                             parse_mode="Markdown", reply_markup=back_kb_fn())
    else:
        await set_setting(key, val)
        await message.answer(f"✅ *تم حفظ {label}!*",
                             parse_mode="Markdown", reply_markup=back_kb_fn())


@router.callback_query(F.data == "edit_about")
async def cb_edit_about(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_about, "about_text",
                       "نص (عن البوت)",
                       "💡 يمكنك استخدام `{owner}` وسيتم استبداله باسم المطور تلقائياً.")


@router.message(AdminFSM.edit_about)
async def save_about(message: Message, state: FSMContext):
    await _save_content(message, state, "about_text", "نص عن البوت", admin_content_kb)


@router.callback_query(F.data == "edit_welcome")
async def cb_edit_welcome(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_welcome, "welcome_text",
                       "رسالة الترحيب",
                       "💡 يمكنك استخدام `{name}` وسيتم استبداله باسم الطالب.")


@router.message(AdminFSM.edit_welcome)
async def save_welcome(message: Message, state: FSMContext):
    await _save_content(message, state, "welcome_text", "رسالة الترحيب", admin_content_kb)


@router.callback_query(F.data == "edit_owner")
async def cb_edit_owner(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_owner, "owner_username",
                       "اسم المطور",
                       "مثال: `@my_username` أو `أحمد محمد`")


@router.message(AdminFSM.edit_owner)
async def save_owner(message: Message, state: FSMContext):
    await _save_content(message, state, "owner_username", "اسم المطور", admin_content_kb)


@router.callback_query(F.data == "edit_camp_info")
async def cb_edit_camp_info(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_camp_info, "camp_info_text",
                       "نص معلومات المعسكر", "")


@router.message(AdminFSM.edit_camp_info)
async def save_camp_info(message: Message, state: FSMContext):
    await _save_content(message, state, "camp_info_text", "نص معلومات المعسكر", admin_content_kb)


@router.callback_query(F.data == "adm_btns_menu")
async def cb_btns_menu(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    s = await get_many_settings("btn_study_plan", "btn_ai", "btn_camp", "btn_about")
    preview = (
        f"📋 *الأزرار الحالية:*\n\n"
        f"1️⃣ `{s['btn_study_plan']}`\n"
        f"2️⃣ `{s['btn_ai']}`\n"
        f"3️⃣ `{s['btn_camp']}`\n"
        f"4️⃣ `{s['btn_about']}`\n\n"
        "اختار الزرار اللي عاوز تعدّله 👇"
    )
    await call.message.edit_text(
        preview, parse_mode="Markdown", reply_markup=admin_btns_kb()
    )
    await call.answer()


async def _ask_btn(call: CallbackQuery, state: FSMContext,
                   st: State, key: str, label: str):
    if not is_owner(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cur = await get_setting(key)
    await state.set_state(st)
    await call.message.edit_text(
        f"🔘 *تعديل زرار: {label}*\n\n"
        f"الحالي: `{cur}`\n\n"
        "اكتب النص الجديد للزرار (مع الإيموجي)\n"
        "أو اكتب `reset` للقيمة الافتراضية.",
        parse_mode="Markdown",
        reply_markup=cancel_kb("adm_btns_menu"),
    )
    await call.answer()


@router.callback_query(F.data == "edit_btn_study")
async def cb_edit_btn_study(call: CallbackQuery, state: FSMContext):
    await _ask_btn(call, state, AdminFSM.edit_btn_study, "btn_study_plan", "خطة المذاكرة")


@router.callback_query(F.data == "edit_btn_ai")
async def cb_edit_btn_ai(call: CallbackQuery, state: FSMContext):
    await _ask_btn(call, state, AdminFSM.edit_btn_ai, "btn_ai", "مستشار الذكاء")


@router.callback_query(F.data == "edit_btn_camp")
async def cb_edit_btn_camp(call: CallbackQuery, state: FSMContext):
    await _ask_btn(call, state, AdminFSM.edit_btn_camp, "btn_camp", "تشغيل المعسكر")


@router.callback_query(F.data == "edit_btn_about")
async def cb_edit_btn_about(call: CallbackQuery, state: FSMContext):
    await _ask_btn(call, state, AdminFSM.edit_btn_about, "btn_about", "عن البوت")


async def _save_btn(message: Message, state: FSMContext, key: str, label: str):
    await state.clear()
    val = message.text.strip()
    if val.lower() == "reset":
        await reset_setting(key)
        await message.answer(f"✅ *تم إعادة زرار {label} للافتراضي!*",
                             parse_mode="Markdown", reply_markup=admin_btns_kb())
    else:
        await set_setting(key, val)
        await message.answer(f"✅ *تم حفظ زرار {label}:*\n`{val}`",
                             parse_mode="Markdown", reply_markup=admin_btns_kb())


@router.message(AdminFSM.edit_btn_study)
async def save_btn_study(message: Message, state: FSMContext):
    await _save_btn(message, state, "btn_study_plan", "خطة المذاكرة")


@router.message(AdminFSM.edit_btn_ai)
async def save_btn_ai(message: Message, state: FSMContext):
    await _save_btn(message, state, "btn_ai", "مستشار الذكاء")


@router.message(AdminFSM.edit_btn_camp)
async def save_btn_camp(message: Message, state: FSMContext):
    await _save_btn(message, state, "btn_camp", "تشغيل المعسكر")


@router.message(AdminFSM.edit_btn_about)
async def save_btn_about(message: Message, state: FSMContext):
    await _save_btn(message, state, "btn_about", "عن البوت")


@router.callback_query(F.data == "edit_dua")
async def cb_edit_dua(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_dua, "camp_dua", "دعاء المعسكر", "")


@router.message(AdminFSM.edit_dua)
async def save_dua(message: Message, state: FSMContext):
    await _save_content(message, state, "camp_dua", "دعاء المعسكر", admin_content_kb)


@router.callback_query(F.data == "edit_lock_msg")
async def cb_edit_lock_msg(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_lock_msg, "camp_lock_msg",
                       "رسالة قفل المعسكر",
                       "💡 متغيرات: `{countdown}` `{start}` `{end}` `{count}`")


@router.message(AdminFSM.edit_lock_msg)
async def save_lock_msg(message: Message, state: FSMContext):
    await _save_content(message, state, "camp_lock_msg", "رسالة قفل المعسكر", admin_content_kb)


@router.callback_query(F.data == "edit_end_msg")
async def cb_edit_end_msg(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_end_msg, "camp_end_msg",
                       "رسالة نهاية المعسكر",
                       "💡 متغير: `{mentions}` وسيتم استبداله بمنشن الأبطال.")


@router.message(AdminFSM.edit_end_msg)
async def save_end_msg(message: Message, state: FSMContext):
    await _save_content(message, state, "camp_end_msg", "رسالة نهاية المعسكر", admin_content_kb)


@router.callback_query(F.data == "edit_stopped_msg")
async def cb_edit_stopped_msg(call: CallbackQuery, state: FSMContext):
    await _ask_content(call, state, AdminFSM.edit_stopped_msg, "camp_stopped_msg",
                       "رسالة إيقاف المعسكر", "")


@router.message(AdminFSM.edit_stopped_msg)
async def save_stopped_msg(message: Message, state: FSMContext):
    await _save_content(message, state, "camp_stopped_msg", "رسالة إيقاف المعسكر", admin_content_kb)


@router.callback_query(F.data == "adm_cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "🛠 *لوحة التحكم الأسطورية* 👑\n\nاختار العملية 👇",
        parse_mode="Markdown",
        reply_markup=admin_menu_kb(),
    )
    await call.answer("✅ تم الإلغاء")
