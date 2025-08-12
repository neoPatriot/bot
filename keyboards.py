from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar
import datetime


def generate_room_selection(room_names, prefix="select_room_"):
    """Генерирует клавиатуру для выбора зала с указанным префиксом"""
    keyboard = []
    for room_id, room_name in room_names.items():
        keyboard.append([
            InlineKeyboardButton(
                room_name,
                callback_data=f"{prefix}{room_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            "Все залы" if prefix == "select_room_" else "Отмена",
            callback_data=f"{prefix}all" if prefix == "select_room_" else "book_cancel"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def generate_calendar(year=None, month=None, selected_room=None, user_id=None,
                      room_names=None, admin_ids=None, room_admins=None, purpose="view"):
    """Генерирует интерактивный календарь с учетом цели (просмотр/бронирование)"""
    now = datetime.datetime.now()
    year = year or now.year
    month = month or now.month

    # Проверка прав администратора
    is_admin = user_id in admin_ids or any(user_id in room_admins.get(rid, []) for rid in room_admins)

    keyboard = [
        [InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="ignore")],
        [InlineKeyboardButton(day, callback_data="ignore") for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]]
    ]

    for week in calendar.monthcalendar(year, month):
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                # Для бронирования разрешаем только будущие даты
                selected_date = datetime.datetime(year, month, day)
                if purpose == "booking" and selected_date.date() < now.date():
                    week_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
                    continue
                elif purpose == "view" and not is_admin and selected_date.date() < now.date():
                    week_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
                    continue

                callback_data = f"select_{year}_{month}_{day}"
                if selected_room and selected_room != "all":
                    callback_data += f"_{selected_room}"
                if purpose == "booking":
                    callback_data += "_book"
                week_buttons.append(InlineKeyboardButton(
                    str(day),
                    callback_data=callback_data
                ))
        keyboard.append(week_buttons)

    # Кнопки навигации
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    nav_buttons = []

    # Для неадминистраторов скрываем кнопку "назад" если это текущий месяц (для просмотра)
    if purpose == "view" and (is_admin or (year > now.year) or (year == now.year and month > now.month)):
        if selected_room:
            callback_data = f"prev_{prev_year}_{prev_month}_{selected_room}"
            if purpose == "booking":
                callback_data += "_book"
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=callback_data))
        else:
            callback_data = f"prev_{prev_year}_{prev_month}"
            if purpose == "booking":
                callback_data += "_book"
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=callback_data))
    elif purpose == "booking" and (year > now.year or (year == now.year and month >= now.month)):
        # Для бронирования всегда показываем навигацию, если месяц не в прошлом
        if selected_room:
            callback_data = f"prev_{prev_year}_{prev_month}_{selected_room}_book"
        else:
            callback_data = f"prev_{prev_year}_{prev_month}_book"
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=callback_data))

    # Всегда показываем кнопку "вперед"
    if selected_room:
        callback_data = f"next_{next_year}_{next_month}_{selected_room}"
        if purpose == "booking":
            callback_data += "_book"
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=callback_data))
    else:
        callback_data = f"next_{next_year}_{next_month}"
        if purpose == "booking":
            callback_data += "_book"
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=callback_data))

    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)