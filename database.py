import aiosqlite
from config import DB_PATH

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    username  TEXT,
    full_name TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS camp_participants (
    user_id   INTEGER,
    camp_id   TEXT,
    username  TEXT,
    full_name TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, camp_id)
);
"""

DEFAULT_SETTINGS: list[tuple[str, str]] = [
    ("force_channel",   ""),
    ("camp_chat_id",    ""),
    ("plan_science",    ""),
    ("plan_math",       ""),
    ("plan_azhar",      ""),
    ("btn_study_plan",  "📚 خطة المذاكرة ⚡"),
    ("btn_ai",          "🧠 مستشار الذكاء الاصطناعي 🔵"),
    ("btn_camp",        "⛺ تشغيل المعسكر 🔴"),
    ("btn_about",       "ℹ️ عن البوت"),
    ("welcome_text",
        "🎉 *أهلاً {name}!*\n\n"
        "🌟 *منظومة معسكرات الثانوية العامة*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "اختار من القائمة 👇"),
    ("about_text",
        "🤖 *منظومة معسكرات الثانوية العامة*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 *المميزات:*\n"
        "• ⛺ نظام معسكرات بعداد تنازلي لايف\n"
        "• 🔒 قفل صارم للجروب مع حذف تلقائي\n"
        "• 👥 منشن جماعي لأبطال المعسكر\n"
        "• 🧠 مستشار ذكاء اصطناعي Gemini\n"
        "• 📚 خطة 30 يوم للشعب الثلاث\n"
        "• 📊 لوحة تحكم متكاملة للمالك\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👑 *المالك والمطور:* {owner}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💪 *ربنا يوفق كل طالب ثانوية عامة!* 🌟"),
    ("owner_username",  "@your_username"),
    ("camp_dua",
        "🤲 «رَبِّ زِدْنِي عِلْمًا وَارْزُقْنِي فَهْمًا»"),
    ("camp_end_msg",
        "🏆 *انتهى المعسكر بنجاح!* 🏆\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑 *عاش يا أبطال المعسكر فوراً!* 🔥\n\n"
        "{mentions}\n\n"
        "💬 *طمنونا عملتوا إيه؟ شاركونا إنجازاتكم!* 🎊\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 *ربنا يكرمكم ويوفقكم في امتحاناتكم!* 🤲"),
    ("camp_lock_msg",
        "⛺ *المعسكر نشط الآن!* 🔴\n\n"
        "⏱ *الوقت المتبقي:* `{countdown}`\n"
        "🕐 *بدأ في:* {start}\n"
        "🕗 *ينتهي في:* {end}\n"
        "👥 *عدد المشاركين:* {count} طالب\n\n"
        "📵 *الشات مقفول — ركّز وذاكر!* 💪\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 *اللهم اجعلنا من أهل العلم والنجاح* 🌟"),
    ("camp_stopped_msg",
        "🔓 *تم إيقاف المعسكر يدوياً!*\n\n"
        "💬 *الشات مفتوح للجميع دلوقتي* 🎊"),
    ("camp_info_text",
        "⛺ *تشغيل المعسكر* 🔴\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *أوامر المالك في الجروب:*\n\n"
        "`/camp 4h` — معسكر 4 ساعات\n"
        "`/camp 30m` — معسكر 30 دقيقة\n"
        "`/camp 1d` — معسكر يوم كامل\n\n"
        "`/stop` — إيقاف المعسكر يدوياً\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ *الإعداد من لوحة الأدمن:*\n"
        "حدد جروب المعسكر أولاً من `/admin`"),
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        for key, val in DEFAULT_SETTINGS:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, val),
            )
        await db.commit()


async def upsert_user(user_id: int, username: str | None, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 username  = excluded.username,
                 full_name = excluded.full_name""",
            (user_id, username or "", full_name),
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            return [r[0] for r in await cur.fetchall()]


async def get_user_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_many_settings(*keys: str) -> dict[str, str]:
    placeholders = ",".join("?" for _ in keys)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT key, value FROM settings WHERE key IN ({placeholders})", keys
        ) as cur:
            rows = await cur.fetchall()
    result = {k: "" for k in keys}
    for row in rows:
        result[row[0]] = row[1]
    return result


async def reset_setting(key: str):
    default_map = {k: v for k, v in DEFAULT_SETTINGS}
    default = default_map.get(key, "")
    await set_setting(key, default)


async def add_camp_participant(
    user_id: int, camp_id: str, username: str | None, full_name: str
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO camp_participants
               (user_id, camp_id, username, full_name)
               VALUES (?, ?, ?, ?)""",
            (user_id, camp_id, username or "", full_name),
        )
        await db.commit()


async def get_camp_participants(camp_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, full_name FROM camp_participants WHERE camp_id = ?",
            (camp_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"user_id": r[0], "username": r[1], "full_name": r[2]} for r in rows]


async def get_camp_count(camp_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM camp_participants WHERE camp_id = ?", (camp_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def clear_camp(camp_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM camp_participants WHERE camp_id = ?", (camp_id,)
        )
        await db.commit()
