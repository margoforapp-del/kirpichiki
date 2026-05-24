import sqlite3
from datetime import datetime, timedelta
import pytz

DB_PATH = "tracker.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def save_entry(date: str, category: str, value: str):
    with sqlite3.connect(DB_PATH) as conn:
        # Удаляем старые записи той же категории за тот же день перед сохранением
        # (для workout — одиночный выбор)
        if category == "workout":
            conn.execute("DELETE FROM entries WHERE date=? AND category=?", (date, category))
        conn.execute(
            "INSERT INTO entries (date, category, value) VALUES (?, ?, ?)",
            (date, category, value)
        )
        conn.commit()


def get_entries(days: int, tz) -> list[dict]:
    today = datetime.now(tz).date()
    start = today - timedelta(days=days - 1)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM entries WHERE date >= ? ORDER BY date DESC",
            (start.isoformat(),)
        ).fetchall()
    return [dict(r) for r in rows]


WORKOUT_LABELS = {
    "none": "❌ Не сделала",
    "short": "⚡ Разминка",
    "full": "💪 Зарядка",
}
CHECKIN_LABELS = {
    "giyur": "📖 Гиюр",
    "english": "🇬🇧 Английский",
    "breath": "🧘 Дыхание",
    "nothing": "—",
}
EVENING_LABELS = {
    "stretch": "🧘 Растяжка",
    "air": "🪟 Проветрила",
    "face": "💆 Фэйс фитнес",
    "nothing": "—",
}


def get_stats(period: str, tz) -> str:
    days = 30 if period == "month" else 7
    entries = get_entries(days, tz)

    # Группируем по дате
    by_date: dict[str, dict] = {}
    for e in entries:
        d = e["date"]
        if d not in by_date:
            by_date[d] = {"workout": [], "checkin": [], "evening": []}
        by_date[d][e["category"]].append(e["value"])

    if not by_date:
        return "📊 Пока нет данных. Начни заполнять трекер!"

    period_label = "7 дней" if days == 7 else "30 дней"
    lines = [f"📊 *Статистика за {period_label}*\n"]

    for date in sorted(by_date.keys(), reverse=True):
        day = by_date[date]
        # Форматируем дату
        dt = datetime.strptime(date, "%Y-%m-%d")
        weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        label = f"{dt.day:02d}.{dt.month:02d} ({weekdays[dt.weekday()]})"

        workout = WORKOUT_LABELS.get(day["workout"][0] if day["workout"] else "", "—")
        checkin = ", ".join(CHECKIN_LABELS.get(v, v) for v in day["checkin"]) or "—"
        evening = ", ".join(EVENING_LABELS.get(v, v) for v in day["evening"]) or "—"

        lines.append(
            f"*{label}*\n"
            f"  🏃 {workout}\n"
            f"  ☀️ {checkin}\n"
            f"  🌙 {evening}\n"
        )

    # Итоговый счёт
    total_days = len(by_date)
    workout_done = sum(
        1 for d in by_date.values()
        if d["workout"] and d["workout"][0] in ("short", "full")
    )
    lines.append(f"─────────────────")
    lines.append(f"💪 Зарядка: *{workout_done}/{total_days}* дней")

    return "\n".join(lines)
