import asyncio
import logging
import google.generativeai as genai
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.menus import back_kb, cancel_kb
from config import GEMINI_API_KEY

router = Router()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "أنت مستشار تعليمي ذكي ومتحمس لطلاب الثانوية العامة المصرية. "
    "ردودك تكون بالعامية المصرية الحماسية وقصيرة ومفيدة جداً. "
    "ساعد الطالب في تنظيم وقته وفهم المواد وحل مشاكله الدراسية. "
    "لا تتجاوز 250 كلمة في الرد."
)

_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    _model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


class AskAIState(StatesGroup):
    waiting = State()


async def ask_gemini(question: str) -> str:
    if not _model:
        return (
            "⚠️ مستشار الذكاء الاصطناعي غير مفعّل حالياً\n\n"
            "المالك لم يضع GEMINI_API_KEY بعد.\n"
            "روح على: https://aistudio.google.com/app/apikey"
        )
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: _model.generate_content(question)
        )
        return resp.text
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            return (
                "⚠️ الـ AI مشغول دلوقتي بسبب كتر الطلبات!\n\n"
                "⏳ استنى دقيقة وحاول تاني 🙏"
            )
        logger.error(f"Gemini error: {e}")
        return f"❌ حدث خطأ في الاتصال بـ AI\nحاول تاني بعد شوية 🔄"


@router.callback_query(F.data == "ask_ai")
async def cb_ask_ai(call: CallbackQuery, state: FSMContext):
    await state.set_state(AskAIState.waiting)
    await call.message.edit_text(
        "🧠 مستشار الذكاء الاصطناعي 🔵\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "اكتب سؤالك أو مشكلتك وهرد عليك فوراً 👇\n\n"
        "💡 أمثلة:\n"
        '• "مش قادر أذاكر فيزياء خالص"\n'
        '• "عندي امتحان بكرا وما ذاكرتش، إيه اللي أعمله؟"\n'
        '• "اعمل لي جدول مذاكرة ليومين"',
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(AskAIState.waiting)
async def handle_question(message: Message, state: FSMContext):
    await state.clear()
    thinking = await message.answer("🧠 جاري التفكير... ⏳")
    answer = await ask_gemini(message.text)
    await thinking.delete()
    await message.answer(
        f"🤖 رد المستشار الذكي:\n\n{answer}",
        reply_markup=back_kb(),
    )
