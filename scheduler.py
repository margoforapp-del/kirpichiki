from datetime import time
from telegram.ext import Application


def setup_scheduler(app: Application, chat_id: int, tz, 
                    send_morning_workout, send_morning_checkin, send_evening):
    
    job_queue = app.job_queue

    # 6:40 — зарядка (воскресенье=6, понедельник=0, ..., четверг=3)
    # В python-telegram-bot days: 0=вс, 1=пн, 2=вт, 3=ср, 4=чт, 5=пт, 6=сб
    job_queue.run_daily(
        send_morning_workout,
        time=time(6, 40, tzinfo=tz),
        days=(0, 1, 2, 3, 4),  # вс, пн, вт, ср, чт
        name="morning_workout_weekdays",
    )

    # 9:00 — зарядка (пятница=5, суббота=6)
    job_queue.run_daily(
        send_morning_workout,
        time=time(9, 0, tzinfo=tz),
        days=(5, 6),  # пт, сб
        name="morning_workout_weekend",
    )

    # 8:00 — утренний чекин (вс-чт)
    job_queue.run_daily(
        send_morning_checkin,
        time=time(8, 0, tzinfo=tz),
        days=(0, 1, 2, 3, 4),  # вс, пн, вт, ср, чт
        name="morning_checkin",
    )

    # 22:00 — вечерний ритуал (каждый день)
    job_queue.run_daily(
        send_evening,
        time=time(22, 0, tzinfo=tz),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="evening",
    )
