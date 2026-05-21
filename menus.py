from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(
    btn_study: str = "📚 خطة المذاكرة ⚡",
    btn_ai: str = "🧠 مستشار الذكاء الاصطناعي 🔵",
    btn_camp: str = "⛺ تشغيل المعسكر 🔴",
    btn_about: str = "ℹ️ عن البوت",
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=btn_study, callback_data="study_plan"),
        InlineKeyboardButton(text=btn_ai,    callback_data="ask_ai"),
    )
    b.row(InlineKeyboardButton(text=btn_camp,  callback_data="camp_info"))
    b.row(InlineKeyboardButton(text=btn_about, callback_data="about"))
    return b.as_markup()


def study_plan_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔬 علمي علوم",  callback_data="plan_science"),
        InlineKeyboardButton(text="📐 علمي رياضة", callback_data="plan_math"),
    )
    b.row(InlineKeyboardButton(text="🕌 القسم الأزهري الشريف", callback_data="plan_azhar"))
    b.row(_back())
    return b.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📢 إذاعة عامة",   callback_data="adm_broadcast"),
        InlineKeyboardButton(text="📊 الإحصائيات",    callback_data="adm_stats"),
    )
    b.row(
        InlineKeyboardButton(text="🔐 قناة الاشتراك", callback_data="adm_channel"),
        InlineKeyboardButton(text="📍 جروب المعسكر",  callback_data="adm_camp_group"),
    )
    b.row(InlineKeyboardButton(text="📝 تعديل الخطط الدراسية", callback_data="adm_plans_menu"))
    b.row(InlineKeyboardButton(text="✏️ تعديل محتوى البوت كله", callback_data="adm_content_menu"))
    return b.as_markup()


def admin_plans_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔬 خطة علمي علوم",        callback_data="adm_plan_science"))
    b.row(InlineKeyboardButton(text="📐 خطة علمي رياضة",       callback_data="adm_plan_math"))
    b.row(InlineKeyboardButton(text="🕌 خطة القسم الأزهري",     callback_data="adm_plan_azhar"))
    b.row(_back_admin())
    return b.as_markup()


def admin_content_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="ℹ️ نص (عن البوت)",          callback_data="edit_about"))
    b.row(InlineKeyboardButton(text="👋 نص رسالة الترحيب",        callback_data="edit_welcome"))
    b.row(InlineKeyboardButton(text="👑 اسم المطور/المالك",        callback_data="edit_owner"))
    b.row(InlineKeyboardButton(text="🔘 أزرار القائمة الرئيسية",  callback_data="adm_btns_menu"))
    b.row(InlineKeyboardButton(text="🤲 دعاء المعسكر",            callback_data="edit_dua"))
    b.row(InlineKeyboardButton(text="🔴 رسالة قفل المعسكر",      callback_data="edit_lock_msg"))
    b.row(InlineKeyboardButton(text="🏆 رسالة نهاية المعسكر",    callback_data="edit_end_msg"))
    b.row(InlineKeyboardButton(text="🔓 رسالة إيقاف المعسكر",    callback_data="edit_stopped_msg"))
    b.row(InlineKeyboardButton(text="⛺ نص معلومات المعسكر",     callback_data="edit_camp_info"))
    b.row(_back_admin())
    return b.as_markup()


def admin_btns_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📚 زرار خطة المذاكرة",        callback_data="edit_btn_study"))
    b.row(InlineKeyboardButton(text="🧠 زرار مستشار الذكاء",        callback_data="edit_btn_ai"))
    b.row(InlineKeyboardButton(text="⛺ زرار تشغيل المعسكر",        callback_data="edit_btn_camp"))
    b.row(InlineKeyboardButton(text="ℹ️ زرار عن البوت",             callback_data="edit_btn_about"))
    b.row(InlineKeyboardButton(text="🔙 رجوع للمحتوى", callback_data="adm_content_menu"))
    return b.as_markup()


def cancel_kb(back_cb: str = "adm_cancel") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌ إلغاء", callback_data=back_cb))
    return b.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(_back())
    return b.as_markup()


def camp_join_kb(camp_id: str, count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=f"👥 انضمام للمعسكر 🟢 ({count})",
        callback_data=f"join:{camp_id}",
    ))
    return b.as_markup()


def subscribe_kb(channel: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="📢 اشترك في القناة",
        url=f"https://t.me/{channel.lstrip('@')}",
    ))
    b.row(InlineKeyboardButton(text="✅ تحققت من اشتراكي", callback_data="check_sub"))
    return b.as_markup()


def _back() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_main")


def _back_admin() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 لوحة التحكم", callback_data="back_admin")
