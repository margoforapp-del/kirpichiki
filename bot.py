import os
import asyncio
import logging
from datetime import datetime, time
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from db import init_db, save_entry, get_stats
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
TZ = pytz.timezone("Asia/Jerusalem")


# ─── УТРЕННЕЕ УВЕДОМЛЕНИЕ (6:40 вск-чт / 9:00 пт-сб) ───────────────────────

async def send_morning_workout(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("❌ Не сделала разминку", callback_data="workout:none")],
        [InlineKeyboardButton("⚡ Разминка до 5 минут", callback_data="workout:short")],
        [InlineKeyboardButton("💪 Зарядка", callback_data="workout:full")],
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🌅 Привет, давай сделаем этот день классным!\n\nКак с зарядкой?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ─── УТРЕННИЙ ЧЕКИН 8:00 (вск-чт) ──────────────────────────────────────────

async def send_morning_checkin(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 5 мин гиюр учёба", callback_data="checkin:giyur")],
        [InlineKeyboardButton("🇬🇧 5 мин английский", callback_data="checkin:english")],
        [InlineKeyboardButton("🧘 3–5 мин дыхание и тишина", callback_data="checkin:breath")],
        [InlineKeyboardButton("✅ Готово!", callback_data="checkin:done")],
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="☀️ Доброе утро! Что успела сделать?\n_(можно выбрать несколько)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── ВЕЧЕРНЕЕ УВЕДОМЛЕНИЕ 22:00 ─────────────────────────────────────────────

async def send_evening(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧘 Растяжка перед сном", callback_data="evening:stretch")],
        [InlineKeyboardButton("🪟 Проветрить комнату", callback_data="evening:air")],
        [InlineKeyboardButton("💆 Фэйс фитнес / массаж лица", callback_data="evening:face")],
        [InlineKeyboardButton("✅ Готово!", callback_data="evening:done")],
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🌙 Вечерний ритуал!\n_(можно выбрать несколько)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── ОБРАБОТКА КНОПОК ────────────────────────────────────────────────────────

# Хранилище временных выборов (в памяти, сбрасывается при рестарте)
user_selections: dict[str, set] = {"checkin": set(), "evening": set()}


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    category, value = data.split(":", 1)
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    # ── WORKOUT ──
    if category == "workout":
        labels = {
            "none": "❌ Не сделала разминку",
            "short": "⚡ Разминка до 5 минут",
            "full": "💪 Зарядка",
        }
        save_entry(today, "workout", value)
        await query.edit_message_text(f"Записала: {labels[value]} 👍")

    # ── CHECKIN (многовыборный) ──
    elif category == "checkin":
        if value == "done":
            selected = user_selections["checkin"]
            if selected:
                for v in selected:
                    save_entry(today, "checkin", v)
            else:
                save_entry(today, "checkin", "nothing")
            user_selections["checkin"] = set()
            await query.edit_message_text("✅ Утренний чекин сохранён! Отличное начало дня 🌟")
        else:
            sel = user_selections["checkin"]
            if value in sel:
                sel.discard(value)
            else:
                sel.add(value)

            icons = {"giyur": "📖", "english": "🇬🇧", "breath": "🧘"}
            names = {"giyur": "5 мин гиюр учёба", "english": "5 мин английский", "breath": "3–5 мин дыхание и тишина"}

            keyboard = []
            for k, name in names.items():
                icon = "✅ " if k in sel else f"{icons[k]} "
                keyboard.append([InlineKeyboardButton(icon + name, callback_data=f"checkin:{k}")])
            keyboard.append([InlineKeyboardButton("💾 Готово!", callback_data="checkin:done")])

            await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))

    # ── EVENING (многовыборный) ──
    elif category == "evening":
        if value == "done":
            selected = user_selections["evening"]
            if selected:
                for v in selected:
                    save_entry(today, "evening", v)
            else:
                save_entry(today, "evening", "nothing")
            user_selections["evening"] = set()
            await query.edit_message_text("✅ Вечерний ритуал сохранён! Спокойной ночи 🌙")
        else:
            sel = user_selections["evening"]
            if value in sel:
                sel.discard(value)
            else:
                sel.add(value)

            icons = {"stretch": "🧘", "air": "🪟", "face": "💆"}
            names = {"stretch": "Растяжка перед сном", "air": "Проветрить комнату", "face": "Фэйс фитнес / массаж лица"}

            keyboard = []
            for k, name in names.items():
                icon = "✅ " if k in sel else f"{icons[k]} "
                keyboard.append([InlineKeyboardButton(icon + name, callback_data=f"evening:{k}")])
            keyboard.append([InlineKeyboardButton("💾 Готово!", callback_data="evening:done")])

            await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))


# ─── РУЧНЫЕ КОМАНДЫ ──────────────────────────────────────────────────────────

async def cmd_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("❌ Не сделала разминку", callback_data="workout:none")],
        [InlineKeyboardButton("⚡ Разминка до 5 минут", callback_data="workout:short")],
        [InlineKeyboardButton("💪 Зарядка", callback_data="workout:full")],
    ]
    await update.message.reply_text(
        "🌅 Привет, давай сделаем этот день классным!\n\nКак с зарядкой?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 5 мин гиюр учёба", callback_data="checkin:giyur")],
        [InlineKeyboardButton("🇬🇧 5 мин английский", callback_data="checkin:english")],
        [InlineKeyboardButton("🧘 3–5 мин дыхание и тишина", callback_data="checkin:breath")],
        [InlineKeyboardButton("✅ Готово!", callback_data="checkin:done")],
    ]
    await update.message.reply_text(
        "☀️ Что успела сделать утром?\n_(можно выбрать несколько)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧘 Растяжка перед сном", callback_data="evening:stretch")],
        [InlineKeyboardButton("🪟 Проветрить комнату", callback_data="evening:air")],
        [InlineKeyboardButton("💆 Фэйс фитнес / массаж лица", callback_data="evening:face")],
        [InlineKeyboardButton("✅ Готово!", callback_data="evening:done")],
    ]
    await update.message.reply_text(
        "🌙 Вечерний ритуал!\n_(можно выбрать несколько)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── КОМАНДА /stats ──────────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    period = args[0] if args else "week"
    text = get_stats(period, TZ)
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── КОМАНДА /start ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой трекер привычек.\n\n"
        "Каждый день буду присылать напоминания сама.\n\n"
        "🕐 Вручную в любое время:\n"
        "/workout — зарядка\n"
        "/checkin — утренний чекин\n"
        "/evening — вечерний ритуал\n\n"
        "📊 Статистика:\n"
        "/stats — за последние 7 дней\n"
        "/stats month — за последние 30 дней"
    )


# ─── ЗАПУСК ──────────────────────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("workout", cmd_workout))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CommandHandler("evening", cmd_evening))
    app.add_handler(CallbackQueryHandler(handle_callback))

    setup_scheduler(app, CHAT_ID, TZ, send_morning_workout, send_morning_checkin, send_evening)

    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
