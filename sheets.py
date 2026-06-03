import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TZ = pytz.timezone("Asia/Jerusalem")

TABS = {
    "утро": "Утро",
    "чекин": "Чекин 8:00",
    "питание": "Питание 20:00",
    "вечер": "Вечер 22:00",
    "меню": "Меню",
}

HEADERS = {
    "утро":    ["Дата", "День", "Зарядка", "Комментарий"],
    "чекин":   ["Дата", "День", "Гиюр", "Английский", "Дыхание", "Комментарий"],
    "питание": ["Дата", "День", "Белок", "Бады", "Овощи/фрукты", "Сканер", "Комментарий"],
    "вечер":   ["Дата", "День", "Растяжка", "Проветрила", "Фэйс фитнес", "Комментарий"],
    "меню":    ["Дата", "День", "Раздел", "Пункт", "Комментарий"],
}


def get_client():
    creds_json = os.environ["GOOGLE_CREDENTIALS"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_sheet(gc, spreadsheet_id, tab_name, headers):
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")
        ws.format("1:1", {"textFormat": {"bold": True}})
    return ws


def today_str():
    now = datetime.now(TZ)
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    return now.strftime("%d.%m.%Y"), weekdays[now.weekday()]


def save_morning(data: dict):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    ws = get_or_create_sheet(gc, sid, TABS["утро"], HEADERS["утро"])
    date, day = today_str()
    ws.append_row([date, day, data.get("workout", ""), data.get("comment", "")],
                  value_input_option="USER_ENTERED")


def save_checkin(data: dict):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    ws = get_or_create_sheet(gc, sid, TABS["чекин"], HEADERS["чекин"])
    date, day = today_str()
    ws.append_row([
        date, day,
        "✓" if "giyur" in data.get("items", []) else "",
        "✓" if "english" in data.get("items", []) else "",
        "✓" if "breath" in data.get("items", []) else "",
        data.get("comment", ""),
    ], value_input_option="USER_ENTERED")


def save_nutrition(data: dict):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    ws = get_or_create_sheet(gc, sid, TABS["питание"], HEADERS["питание"])
    date, day = today_str()
    ws.append_row([
        date, day,
        "✓" if "protein" in data.get("items", []) else "",
        "✓" if "supplements" in data.get("items", []) else "",
        "✓" if "veggies" in data.get("items", []) else "",
        "✓" if "scanner" in data.get("items", []) else "",
        data.get("comment", ""),
    ], value_input_option="USER_ENTERED")


def save_evening(data: dict):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    ws = get_or_create_sheet(gc, sid, TABS["вечер"], HEADERS["вечер"])
    date, day = today_str()
    ws.append_row([
        date, day,
        "✓" if "stretch" in data.get("items", []) else "",
        "✓" if "air" in data.get("items", []) else "",
        "✓" if "face" in data.get("items", []) else "",
        data.get("comment", ""),
    ], value_input_option="USER_ENTERED")


def save_menu(section: str, item: str, comment: str = ""):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    ws = get_or_create_sheet(gc, sid, TABS["меню"], HEADERS["меню"])
    date, day = today_str()
    ws.append_row([date, day, section, item, comment],
                  value_input_option="USER_ENTERED")


def get_stats_data(days: int):
    gc = get_client()
    sid = os.environ["SPREADSHEET_ID"]
    sh = gc.open_by_key(sid)
    result = {}
    for key, tab_name in TABS.items():
        try:
            ws = sh.worksheet(tab_name)
            result[key] = ws.get_all_records()
        except gspread.WorksheetNotFound:
            result[key] = []
    return result
