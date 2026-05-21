from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import get_setting
from config import OWNER_ID
from keyboards.menus import subscribe_kb


class SubscribeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = event.from_user
        if not user or user.id == OWNER_ID:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)

        channel = await get_setting("force_channel")
        if not channel:
            return await handler(event, data)

        bot = data["bot"]
        try:
            member = await bot.get_chat_member(channel, user.id)
            if member.status in ("left", "kicked", "restricted"):
                raise PermissionError
        except Exception:
            text = (
                "⛔ *عشان تستخدم البوت لازم تشترك في القناة الرسمية أولاً!*\n\n"
                "اضغط على الزرار أدناه 👇 ثم اضغط ✅"
            )
            kb = subscribe_kb(channel)
            if isinstance(event, Message):
                await event.answer(text, parse_mode="Markdown", reply_markup=kb)
            else:
                await event.answer("⛔ اشترك في القناة أولاً!", show_alert=True)
            return

        return await handler(event, data)
