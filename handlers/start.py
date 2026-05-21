from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from database import upsert_user, get_setting, get_many_settings
from keyboards.menus import main_menu_kb, study_plan_kb, back_kb, subscribe_kb
from config import OWNER_ID

router = Router()

PLAN_SCIENCE_DEFAULT = (
    "🔬 *خطة المذاكرة 30 يوم — علمي علوم*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📅 *الأسبوع الأول (أيام 1-7): أساسيات القوة*\n"
    "• يوم 1-2: أحياء — الخلية ووظائفها\n"
    "• يوم 3-4: كيمياء — الذرة والجدول الدوري\n"
    "• يوم 5-6: فيزياء — الحركة والقوى\n"
    "• يوم 7: مراجعة + حل أسئلة الأسبوع\n\n"
    "📅 *الأسبوع الثاني (أيام 8-14): التعمق*\n"
    "• يوم 8-9: أحياء — الجهاز العصبي والحواس\n"
    "• يوم 10-11: كيمياء — التفاعلات والمعادلات\n"
    "• يوم 12-13: فيزياء — الكهرباء والمغناطيسية\n"
    "• يوم 14: مراجعة شاملة للأسبوعين\n\n"
    "📅 *الأسبوع الثالث (أيام 15-21): المواد الأدبية*\n"
    "• يوم 15-16: عربي — النحو والصرف\n"
    "• يوم 17-18: إنجليزي — Grammar + Vocabulary\n"
    "• يوم 19-20: أحياء — التكاثر والوراثة\n"
    "• يوم 21: اختبار نفسك في كل المواد\n\n"
    "📅 *الأسبوع الرابع (أيام 22-30): المراجعة النهائية*\n"
    "• يوم 22-24: مراجعة الأحياء والكيمياء\n"
    "• يوم 25-27: مراجعة الفيزياء والرياضة\n"
    "• يوم 28-29: حل نماذج امتحانات سابقة\n"
    "• يوم 30: راحة + مراجعة خفيفة + نوم مبكر\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🌟 *ربنا يوفقك يا بطل العلوم!* 💪"
)

PLAN_MATH_DEFAULT = (
    "📐 *خطة المذاكرة 30 يوم — علمي رياضة*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📅 *الأسبوع الأول (أيام 1-7): أسس الرياضة*\n"
    "• يوم 1-2: جبر — المتتاليات والمتسلسلات\n"
    "• يوم 3-4: هندسة — المثلثات والدوائر\n"
    "• يوم 5-6: فيزياء — الديناميكا والحركة\n"
    "• يوم 7: مراجعة + حل تمارين الأسبوع\n\n"
    "📅 *الأسبوع الثاني (أيام 8-14): التعمق الرياضي*\n"
    "• يوم 8-9: تفاضل وتكامل — المشتقات\n"
    "• يوم 10-11: جبر — المصفوفات والمحددات\n"
    "• يوم 12-13: فيزياء — الكهرباء والضوء\n"
    "• يوم 14: مراجعة شاملة للأسبوعين\n\n"
    "📅 *الأسبوع الثالث (أيام 15-21): المواد الأخرى*\n"
    "• يوم 15-16: عربي — البلاغة والنحو\n"
    "• يوم 17-18: إنجليزي — Grammar + Writing\n"
    "• يوم 19-20: تكامل — المساحات والحجوم\n"
    "• يوم 21: اختبار نفسك في كل المواد\n\n"
    "📅 *الأسبوع الرابع (أيام 22-30): المراجعة النهائية*\n"
    "• يوم 22-24: مراجعة الجبر والهندسة\n"
    "• يوم 25-27: مراجعة التفاضل والتكامل\n"
    "• يوم 28-29: نماذج امتحانات رياضة سابقة\n"
    "• يوم 30: راحة + مراجعة خفيفة + نوم مبكر\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🌟 *ربنا يوفقك يا نجم الرياضيات!* 💪"
)

PLAN_AZHAR_DEFAULT = (
    "🕌 *خطة المذاكرة 30 يوم — القسم الأزهري*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📅 *الأسبوع الأول (أيام 1-7): العلوم الشرعية*\n"
    "• يوم 1-2: تفسير — سورة البقرة وآل عمران\n"
    "• يوم 3-4: فقه — العبادات وأحكامها\n"
    "• يوم 5-6: توحيد — صفات الله وأركان الإيمان\n"
    "• يوم 7: مراجعة + حفظ المتون\n\n"
    "📅 *الأسبوع الثاني (أيام 8-14): اللغة العربية*\n"
    "• يوم 8-9: نحو — الجملة الاسمية والفعلية\n"
    "• يوم 10-11: صرف — الميزان الصرفي والأوزان\n"
    "• يوم 12-13: بلاغة — البيان والبديع والمعاني\n"
    "• يوم 14: مراجعة شاملة للأسبوعين\n\n"
    "📅 *الأسبوع الثالث (أيام 15-21): المواد العلمية*\n"
    "• يوم 15-16: رياضيات — الجبر والهندسة\n"
    "• يوم 17-18: إنجليزي — Grammar + Vocabulary\n"
    "• يوم 19-20: حديث شريف — المتن والشرح\n"
    "• يوم 21: اختبار نفسك في كل المواد\n\n"
    "📅 *الأسبوع الرابع (أيام 22-30): المراجعة النهائية*\n"
    "• يوم 22-24: مراجعة التفسير والفقه والتوحيد\n"
    "• يوم 25-27: مراجعة اللغة العربية بالكامل\n"
    "• يوم 28-29: نماذج امتحانات أزهرية سابقة\n"
    "• يوم 30: راحة + دعاء + مراجعة خفيفة\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🌟 *ربنا يوفقك ويبارك في علمك!* 🤲"
)


async def _main_menu_dynamic() -> InlineKeyboardMarkup:
    s = await get_many_settings(
        "btn_study_plan", "btn_ai", "btn_camp", "btn_about"
    )
    return main_menu_kb(
        btn_study=s["btn_study_plan"] or "📚 خطة المذاكرة ⚡",
        btn_ai=s["btn_ai"]           or "🧠 مستشار الذكاء الاصطناعي 🔵",
        btn_camp=s["btn_camp"]       or "⛺ تشغيل المعسكر 🔴",
        btn_about=s["btn_about"]     or "ℹ️ عن البوت",
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    await upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    channel = await get_setting("force_channel")
    if channel and message.from_user.id != OWNER_ID:
        try:
            member = await message.bot.get_chat_member(channel, message.from_user.id)
            if member.status in ("left", "kicked", "restricted"):
                raise PermissionError
        except Exception:
            await message.answer(
                "⛔ *لازم تشترك في القناة الرسمية أولاً!*",
                parse_mode="Markdown",
                reply_markup=subscribe_kb(channel),
            )
            return

    welcome = await get_setting("welcome_text")
    if not welcome:
        welcome = (
            "🎉 *أهلاً {name}!*\n\n"
            "🌟 *منظومة معسكرات الثانوية العامة*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "اختار من القائمة 👇"
        )
    text = welcome.replace("{name}", message.from_user.first_name)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=await _main_menu_dynamic(),
    )


@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    await call.answer("✅ تم! ابعت /start مجدداً", show_alert=True)


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    await upsert_user(
        call.from_user.id,
        call.from_user.username,
        call.from_user.full_name,
    )
    await call.message.edit_text(
        "🏠 *القائمة الرئيسية*\n\nاختار من القائمة 👇",
        parse_mode="Markdown",
        reply_markup=await _main_menu_dynamic(),
    )
    await call.answer()


@router.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    s = await get_many_settings("about_text", "owner_username")
    text = s["about_text"] or ""
    owner = s["owner_username"] or "@your_username"
    owner_safe = owner.replace("_", "\\_").replace("*", "\\*")
    text = text.replace("{owner}", owner_safe)
    await call.message.edit_text(
        text, parse_mode="Markdown", reply_markup=back_kb()
    )
    await call.answer()


@router.callback_query(F.data == "camp_info")
async def cb_camp_info(call: CallbackQuery):
    text = await get_setting("camp_info_text")
    await call.message.edit_text(
        text, parse_mode="Markdown", reply_markup=back_kb()
    )
    await call.answer()


@router.callback_query(F.data == "study_plan")
async def cb_study_plan(call: CallbackQuery):
    await call.message.edit_text(
        "📚 *خطة المذاكرة ⚡*\n\nاختار شعبتك 👇",
        parse_mode="Markdown",
        reply_markup=study_plan_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "plan_science")
async def cb_plan_science(call: CallbackQuery):
    text = await get_setting("plan_science")
    await call.message.edit_text(
        text or PLAN_SCIENCE_DEFAULT, parse_mode="Markdown", reply_markup=back_kb()
    )
    await call.answer()


@router.callback_query(F.data == "plan_math")
async def cb_plan_math(call: CallbackQuery):
    text = await get_setting("plan_math")
    await call.message.edit_text(
        text or PLAN_MATH_DEFAULT, parse_mode="Markdown", reply_markup=back_kb()
    )
    await call.answer()


@router.callback_query(F.data == "plan_azhar")
async def cb_plan_azhar(call: CallbackQuery):
    text = await get_setting("plan_azhar")
    await call.message.edit_text(
        text or PLAN_AZHAR_DEFAULT, parse_mode="Markdown", reply_markup=back_kb()
    )
    await call.answer()
