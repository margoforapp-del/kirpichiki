import os
import logging
from datetime import time
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

import sheets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
TZ = pytz.timezone("Asia/Jerusalem")

state = {}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📋 Меню", "💪 Зарядка"],
        ["☀️ Чекин", "🥗 Питание"],
        ["🌙 Вечер", "📊 Статистика"],
    ],
    resize_keyboard=True,
)


# ─── КЛАВИАТУРЫ ──────────────────────────────────────────────────────────────

def workout_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Не сделала разминку", callback_data="workout:none")],
        [InlineKeyboardButton("⚡ Разминка до 5 минут", callback_data="workout:short")],
        [InlineKeyboardButton("💪 Зарядка", callback_data="workout:full")],
        [InlineKeyboardButton("✏️ Другое", callback_data="workout:other")],
    ])


def checkin_keyboard(selected: set):
    items = [
        ("giyur", "📖 5 мин гиюр учёба"),
        ("english", "🇬🇧 5 мин английский"),
        ("breath", "🧘 3–5 мин дыхание и тишина"),
    ]
    rows = []
    for k, name in items:
        label = ("✅ " if k in selected else "") + name
        rows.append([InlineKeyboardButton(label, callback_data=f"checkin:{k}")])
    rows.append([InlineKeyboardButton("✏️ Комментарий", callback_data="checkin:comment")])
    rows.append([InlineKeyboardButton("💾 Сохранить", callback_data="checkin:done")])
    return InlineKeyboardMarkup(rows)


def nutrition_keyboard(selected: set):
    items = [
        ("protein", "🥩 Достаточно белка"),
        ("supplements", "💊 Бады"),
        ("veggies", "🥗 Овощи / фрукты"),
        ("scanner", "🧘 Упражнение сканер"),
    ]
    rows = []
    for k, name in items:
        label = ("✅ " if k in selected else "") + name
        rows.append([InlineKeyboardButton(label, callback_data=f"nutrition:{k}")])
    rows.append([InlineKeyboardButton("✏️ Комментарий", callback_data="nutrition:comment")])
    rows.append([InlineKeyboardButton("💾 Сохранить", callback_data="nutrition:done")])
    return InlineKeyboardMarkup(rows)


def evening_keyboard(selected: set):
    items = [
        ("stretch", "🧘 Растяжка перед сном"),
        ("air", "🪟 Проветрить комнату"),
        ("face", "💆 Фэйс фитнес / массаж лица"),
    ]
    rows = []
    for k, name in items:
        label = ("✅ " if k in selected else "") + name
        rows.append([InlineKeyboardButton(label, callback_data=f"evening:{k}")])
    rows.append([InlineKeyboardButton("✏️ Комментарий", callback_data="evening:comment")])
    rows.append([InlineKeyboardButton("💾 Сохранить", callback_data="evening:done")])
    return InlineKeyboardMarkup(rows)


def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Хасл", callback_data="menu:section:хасл")],
        [InlineKeyboardButton("🌱 Развитие", callback_data="menu:section:развитие")],
        [InlineKeyboardButton("🏅 Спорт", callback_data="menu:section:спорт")],
        [InlineKeyboardButton("💌 Переписка", callback_data="menu:section:переписка")],
        [InlineKeyboardButton("📞 Созвон с близкими", callback_data="menu:section:созвон")],
        [InlineKeyboardButton("🎉 Социализация", callback_data="menu:section:социализация")],
        [InlineKeyboardButton("💅 Уход за собой", callback_data="menu:section:уход")],
        [InlineKeyboardButton("🏠 Дом", callback_data="menu:section:дом")],
    ])


MENU_ITEMS = {
    "хасл": [
        ("работа", "💼 Работа"),
        ("проект", "🎯 Работа над проектом"),
        ("бэ", "🥊 Тренировки Б.Э"),
        ("урок", "👩‍🏫 Провела урок"),
    ],
    "бэ_sub": [
        ("группа", "👥 Группа"),
        ("рои", "🥋 Рои"),
        ("доп", "➕ Дополнительный"),
    ],
    "развитие": [
        ("учеба", "📚 Учёба"),
        ("свп", "🔹 СВП"),
        ("шахматы", "♟ Шахматы"),
        ("гиюр", "📖 Учёба гиюр"),
        ("чтение", "📕 Чтение"),
        ("письмо", "✍️ Письменное слово"),
    ],
    "спорт": [
        ("джиу", "🥋 Джиу"),
        ("растяжка", "🤸 Растяжка"),
        ("вес", "🏋️ Тренировка с весом"),
        ("фитнес", "🏃 Фитнес"),
        ("ходьба", "🚶 Ходьба"),
    ],
    "переписка": [
        ("мама_п", "👩 Мамой"),
        ("ру_п", "👤 Ру"),
        ("папа_п", "👨 Папой"),
        ("игаль_п", "👤 Игалем"),
    ],
    "созвон": [
        ("мама_с", "👩 Мамой"),
        ("ру_с", "👤 Ру"),
        ("папа_с", "👨 Папой"),
        ("игаль_с", "👤 Игалем"),
    ],
    "социализация": [],
    "уход": [
        ("ногти", "💅 Ногти"),
        ("брови", "🪮 Брови"),
        ("ресницы", "👁 Ресницы"),
        ("волосы", "✂️ Кончики волос"),
    ],
    "дом": [
        ("уборка", "🧹 Поддержание чистоты"),
        ("готовка", "🍳 Готовка"),
    ],
}

SECTION_NAMES = {
    "хасл": "Хасл",
    "развитие": "Развитие",
    "спорт": "Спорт",
    "переписка": "Переписка",
    "созвон": "Созвон",
    "социализация": "Социализация",
    "уход": "Уход за собой",
    "дом": "Дом",
}


def section_keyboard(section: str, selected: set):
    items = MENU_ITEMS.get(section, [])
    rows = []
    for k, name in items:
        label = ("✅ " if k in selected else "") + name
        rows.append([InlineKeyboardButton(label, callback_data=f"menu:item:{section}:{k}")])
    rows.append([InlineKeyboardButton("✏️ Комментарий", callback_data=f"menu:comment:{section}")])
    rows.append([InlineKeyboardButton("💾 Сохранить", callback_data=f"menu:done:{section}")])
    rows.append([InlineKeyboardButton("« Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(rows)


def be_keyboard(selected: set):
    rows = []
    for k, name in MENU_ITEMS["бэ_sub"]:
        label = ("✅ " if k in selected else "") + name
        rows.append([InlineKeyboardButton(label, callback_data=f"menu:be:{k}")])
    rows.append([InlineKeyboardButton("✏️ Комментарий", callback_data="menu:be_comment")])
    rows.append([InlineKeyboardButton("💾 Сохранить", callback_data="menu:be_done")])
    rows.append([InlineKeyboardButton("« Назад", callback_data="menu:section:хасл")])
    return InlineKeyboardMarkup(rows)


# ─── УВЕДОМЛЕНИЯ ─────────────────────────────────────────────────────────────

async def send_morning_workout(context):
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🌅 Привет, давай сделаем этот день классным!\n\nКак с зарядкой?",
        reply_markup=workout_keyboard(),
    )

async def send_morning_checkin(context):
    state["checkin"] = {"items": set(), "comment": ""}
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="☀️ Доброе утро! Что успела сделать?\n_можно выбрать несколько_",
        reply_markup=checkin_keyboard(set()),
        parse_mode="Markdown",
    )

async def send_nutrition(context):
    state["nutrition"] = {"items": set(), "comment": ""}
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🥗 Вечерний чекин питания\n_можно выбрать несколько_",
        reply_markup=nutrition_keyboard(set()),
        parse_mode="Markdown",
    )

async def send_evening(context):
    state["evening"] = {"items": set(), "comment": ""}
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🌙 Вечерний ритуал!\n_можно выбрать несколько_",
        reply_markup=evening_keyboard(set()),
        parse_mode="Markdown",
    )


# ─── ОБРАБОТКА КНОПОК ────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("workout:"):
        val = data.split(":")[1]
        if val == "other":
            state["waiting_comment_for"] = "workout_other"
            await context.bot.send_message(chat_id=CHAT_ID, text="✏️ Напиши что делала:")
            return
        labels = {"none": "❌ Не делала", "short": "⚡ Разминка до 5 мин", "full": "💪 Зарядка"}
        try:
            sheets.save_morning({"workout": labels[val], "comment": ""})
        except Exception as e:
            logger.error(f"Sheets error: {e}")
        await query.edit_message_text(f"Записала: {labels[val]} 👍")

    elif data.startswith("checkin:"):
        val = data.split(":")[1]
        if "checkin" not in state:
            state["checkin"] = {"items": set(), "comment": ""}
        if val == "comment":
            state["waiting_comment_for"] = "checkin"
            await context.bot.send_message(chat_id=CHAT_ID, text="✏️ Напиши комментарий, потом нажми 💾 Сохранить:")
            return
        elif val == "done":
            try:
                sheets.save_checkin({"items": list(state["checkin"]["items"]), "comment": state["checkin"].get("comment", "")})
            except Exception as e:
                logger.error(f"Sheets error: {e}")
            state.pop("checkin", None)
            await query.edit_message_text("✅ Утренний чекин сохранён! 🌟")
        else:
            sel = state["checkin"]["items"]
            sel.discard(val) if val in sel else sel.add(val)
            await query.edit_message_reply_markup(checkin_keyboard(sel))

    elif data.startswith("nutrition:"):
        val = data.split(":")[1]
        if "nutrition" not in state:
            state["nutrition"] = {"items": set(), "comment": ""}
        if val == "comment":
            state["waiting_comment_for"] = "nutrition"
            await context.bot.send_message(chat_id=CHAT_ID, text="✏️ Напиши комментарий, потом нажми 💾 Сохранить:")
            return
        elif val == "done":
            try:
                sheets.save_nutrition({"items": list(state["nutrition"]["items"]), "comment": state["nutrition"].get("comment", "")})
            except Exception as e:
                logger.error(f"Sheets error: {e}")
            state.pop("nutrition", None)
            await query.edit_message_text("✅ Питание сохранено! 🥗")
        else:
            sel = state["nutrition"]["items"]
            sel.discard(val) if val in sel else sel.add(val)
            await query.edit_message_reply_markup(nutrition_keyboard(sel))

    elif data.startswith("evening:"):
        val = data.split(":")[1]
        if "evening" not in state:
            state["evening"] = {"items": set(), "comment": ""}
        if val == "comment":
            state["waiting_comment_for"] = "evening"
            await context.bot.send_message(chat_id=CHAT_ID, text="✏️ Напиши комментарий, потом нажми 💾 Сохранить:")
            return
        elif val == "done":
            try:
                sheets.save_evening({"items": list(state["evening"]["items"]), "comment": state["evening"].get("comment", "")})
            except Exception as e:
                logger.error(f"Sheets error: {e}")
            state.pop("evening", None)
            await query.edit_message_text("✅ Вечерний ритуал сохранён! 🌙")
        else:
            sel = state["evening"]["items"]
            sel.discard(val) if val in sel else sel.add(val)
            await query.edit_message_reply_markup(evening_keyboard(sel))

    elif data.startswith("menu:"):
        parts = data.split(":")
        action = parts[1]

        if action == "back":
            await query.edit_message_text("📋 Меню — выбери раздел:", reply_markup=menu_keyboard())

        elif action == "section":
            section = parts[2]
            if section == "социализация":
                state["waiting_comment_for"] = "menu_social"
                await context.bot.send_message(chat_id=CHAT_ID, text="🎉 Социализация — напиши что было:")
                return
            state.setdefault("menu_sel", {})[section] = state.get("menu_sel", {}).get(section, set())
            await query.edit_message_text(
                f"📋 {SECTION_NAMES.get(section, section)}",
                reply_markup=section_keyboard(section, state["menu_sel"].get(section, set()))
            )

        elif action == "item":
            section = parts[2]
            item = parts[3]
            if item == "бэ":
                state.setdefault("menu_sel", {}).setdefault("бэ", set())
                await query.edit_message_text("🥊 Тренировки Б.Э — выбери тип:", reply_markup=be_keyboard(state["menu_sel"].get("бэ", set())))
                return
            state.setdefault("menu_sel", {}).setdefault(section, set())
            sel = state["menu_sel"][section]
            sel.discard(item) if item in sel else sel.add(item)
            await query.edit_message_reply_markup(section_keyboard(section, sel))

        elif action == "be":
            item = parts[2]
            state.setdefault("menu_sel", {}).setdefault("бэ", set())
            sel = state["menu_sel"]["бэ"]
            sel.discard(item) if item in sel else sel.add(item)
            await query.edit_message_reply_markup(be_keyboard(sel))

        elif action == "be_comment":
            state["waiting_comment_for"] = "menu_be"
            await context.bot.send_message(chat_id=CHAT_ID, text="✏️ Напиши комментарий к тренировке Б.Э:")

        elif action == "be_done":
            sel = state.get("menu_sel", {}).get("бэ", set())
            labels = {"группа": "Группа", "рои": "Рои", "доп": "Дополнительный"}
            for item in sel:
                try:
                    sheets.save_menu("Хасл — Тренировки Б.Э", labels.get(item, item), state.get("be_comment", ""))
                except Exception as e:
                    logger.error(f"Sheets error: {e}")
            state.get("menu_sel", {}).pop("бэ", None)
            state.pop("be_comment", None)
            await query.edit_message_text("✅ Тренировки Б.Э сохранены!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Меню", callback_data="menu:back")]]))

        elif action == "comment":
            section = parts[2]
            state["waiting_comment_for"] = f"menu_{section}"
            await context.bot.send_message(chat_id=CHAT_ID, text=f"✏️ Комментарий к {SECTION_NAMES.get(section, section)}, потом нажми 💾 Сохранить:")

        elif action == "done":
            section = parts[2]
            sel = state.get("menu_sel", {}).get(section, set())
            item_labels = {k: v for k, v in MENU_ITEMS.get(section, [])}
            comment = state.get(f"comment_{section}", "")
            saved = False
            for item in sel:
                try:
                    sheets.save_menu(SECTION_NAMES.get(section, section), item_labels.get(item, item), comment)
                    saved = True
                except Exception as e:
                    logger.error(f"Sheets error: {e}")
            if not sel and comment:
                try:
                    sheets.save_menu(SECTION_NAMES.get(section, section), "", comment)
                    saved = True
                except Exception as e:
                    logger.error(f"Sheets error: {e}")
            state.get("menu_sel", {}).pop(section, None)
            state.pop(f"comment_{section}", None)
            await query.edit_message_text(f"✅ {SECTION_NAMES.get(section, section)} сохранено!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Меню", callback_data="menu:back")]]))

    elif data.startswith("stats:"):
        period = data.split(":")[1]
        text = build_stats(period)
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Неделя", callback_data="stats:week"),
                 InlineKeyboardButton("🗓 Месяц", callback_data="stats:month")]
            ]))


# ─── ОБРАБОТКА ТЕКСТА ────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Кнопки постоянной клавиатуры
    if text == "📋 Меню":
        state["menu_sel"] = {}
        await update.message.reply_text("📋 Меню — выбери раздел:", reply_markup=menu_keyboard())
        return
    elif text == "💪 Зарядка":
        await update.message.reply_text("🌅 Как с зарядкой?", reply_markup=workout_keyboard())
        return
    elif text == "☀️ Чекин":
        state["checkin"] = {"items": set(), "comment": ""}
        await update.message.reply_text("☀️ Что успела сделать утром?", reply_markup=checkin_keyboard(set()))
        return
    elif text == "🥗 Питание":
        state["nutrition"] = {"items": set(), "comment": ""}
        await update.message.reply_text("🥗 Питание и здоровье", reply_markup=nutrition_keyboard(set()))
        return
    elif text == "🌙 Вечер":
        state["evening"] = {"items": set(), "comment": ""}
        await update.message.reply_text("🌙 Вечерний ритуал!", reply_markup=evening_keyboard(set()))
        return
    elif text == "📊 Статистика":
        t = build_stats("week")
        await update.message.reply_text(t, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Неделя", callback_data="stats:week"),
                 InlineKeyboardButton("🗓 Месяц", callback_data="stats:month")]
            ]))
        return

    # Обработка комментариев
    waiting = state.get("waiting_comment_for")
    if not waiting:
        return

    state.pop("waiting_comment_for", None)

    if waiting == "workout_other":
        try:
            sheets.save_morning({"workout": text, "comment": ""})
        except Exception as e:
            logger.error(f"Sheets error: {e}")
        await update.message.reply_text(f"Записала: {text} 👍")

    elif waiting == "checkin":
        state.setdefault("checkin", {})["comment"] = text
        await update.message.reply_text("✅ Комментарий добавлен!")

    elif waiting == "nutrition":
        state.setdefault("nutrition", {})["comment"] = text
        await update.message.reply_text("✅ Комментарий добавлен!")

    elif waiting == "evening":
        state.setdefault("evening", {})["comment"] = text
        await update.message.reply_text("✅ Комментарий добавлен!")

    elif waiting == "menu_social":
        try:
            sheets.save_menu("Социализация", "", text)
        except Exception as e:
            logger.error(f"Sheets error: {e}")
        await update.message.reply_text("✅ Социализация сохранена! 🎉")

    elif waiting == "menu_be":
        state["be_comment"] = text
        await update.message.reply_text("✅ Комментарий добавлен!")

    elif waiting and waiting.startswith("menu_"):
        section = waiting.replace("menu_", "")
        state[f"comment_{section}"] = text
        await update.message.reply_text("✅ Комментарий добавлен!")


# ─── СТАТИСТИКА ──────────────────────────────────────────────────────────────

def build_stats(period: str) -> str:
    try:
        data = sheets.get_stats_data(7 if period == "week" else 30)
    except Exception as e:
        return f"⚠️ Ошибка загрузки данных: {e}"

    label = "7 дней" if period == "week" else "30 дней"
    lines = [f"📊 *Статистика за {label}*\n"]

    morning = data.get("утро", [])
    workout_done = sum(1 for r in morning if r.get("Зарядка") not in ("", "❌ Не делала"))
    lines.append(f"💪 Зарядка: *{workout_done}/{len(morning)}* дней")

    checkin = data.get("чекин", [])
    if checkin:
        giyur = sum(1 for r in checkin if r.get("Гиюр") == "✓")
        english = sum(1 for r in checkin if r.get("Английский") == "✓")
        breath = sum(1 for r in checkin if r.get("Дыхание") == "✓")
        lines.append(f"📖 Гиюр: *{giyur}/{len(checkin)}* дней")
        lines.append(f"🇬🇧 Английский: *{english}/{len(checkin)}* дней")
        lines.append(f"🧘 Дыхание: *{breath}/{len(checkin)}* дней")

    nutrition = data.get("питание", [])
    if nutrition:
        protein = sum(1 for r in nutrition if r.get("Белок") == "✓")
        lines.append(f"🥩 Белок: *{protein}/{len(nutrition)}* дней")

    evening = data.get("вечер", [])
    if evening:
        stretch = sum(1 for r in evening if r.get("Растяжка") == "✓")
        lines.append(f"🧘 Растяжка: *{stretch}/{len(evening)}* дней")

    menu = data.get("меню", [])
    if menu:
        from collections import Counter
        sections = Counter(r.get("Раздел", "") for r in menu if r.get("Раздел"))
        lines.append("\n*Активность по разделам:*")
        for section, count in sections.most_common():
            lines.append(f"  {section}: {count} раз")

    return "\n".join(lines)


# ─── КОМАНДЫ ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой трекер Кирпичики.\n\nКнопки внизу — всегда доступны 👇",
        reply_markup=MAIN_KEYBOARD,
    )

async def cmd_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌅 Как с зарядкой?", reply_markup=workout_keyboard())

async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state["checkin"] = {"items": set(), "comment": ""}
    await update.message.reply_text("☀️ Что успела сделать утром?", reply_markup=checkin_keyboard(set()))

async def cmd_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state["nutrition"] = {"items": set(), "comment": ""}
    await update.message.reply_text("🥗 Питание и здоровье", reply_markup=nutrition_keyboard(set()))

async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state["evening"] = {"items": set(), "comment": ""}
    await update.message.reply_text("🌙 Вечерний ритуал!", reply_markup=evening_keyboard(set()))

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state["menu_sel"] = {}
    await update.message.reply_text("📋 Меню — выбери раздел:", reply_markup=menu_keyboard())

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    period = "month" if args and args[0] == "month" else "week"
    text = build_stats(period)
    await update.message.reply_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Неделя", callback_data="stats:week"),
             InlineKeyboardButton("🗓 Месяц", callback_data="stats:month")]
        ]))


# ─── ПЛАНИРОВЩИК ─────────────────────────────────────────────────────────────

def setup_scheduler(app):
    jq = app.job_queue
    jq.run_daily(send_morning_workout, time=time(6, 40, tzinfo=TZ), days=(0, 1, 2, 3, 4))
    jq.run_daily(send_morning_workout, time=time(9, 0, tzinfo=TZ), days=(5, 6))
    jq.run_daily(send_morning_checkin, time=time(8, 0, tzinfo=TZ), days=(0, 1, 2, 3, 4))
    jq.run_daily(send_nutrition, time=time(20, 0, tzinfo=TZ), days=(0, 1, 2, 3, 4, 5, 6))
    jq.run_daily(send_evening, time=time(22, 0, tzinfo=TZ), days=(0, 1, 2, 3, 4, 5, 6))


# ─── ЗАПУСК ──────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("workout", cmd_workout))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CommandHandler("nutrition", cmd_nutrition))
    app.add_handler(CommandHandler("evening", cmd_evening))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    setup_scheduler(app)

    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
