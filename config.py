from telegram import KeyboardButton

# Конфигурационные константы
TOKEN = "7973585745:AAFz97T9MoptzcuatQKy3pd1zbd9J-o9f5E"  # Замените на ваш токен

ADMIN_USER_IDS = [1098521522, 1042197487, 1928520826, 810564487]
ROOM_ADMINS = {
    1: [],  # Администраторы для комнаты 1
    2: [],  # Администраторы для комнаты 2
    3: [],  # Администраторы для комнаты 3
    4: [],  # Администраторы для комнаты 4
    5: []   # Администраторы для комнаты 5
}

ROOM_NAMES = {
    1: 'Чертог "Z-Studio"',
    3: '"Кузня" РОК-школы "Z-school"',
    4: '"Певческая" РОК-школы "Z-school"',
    5: '"Гитарные покои" РОК-школы "Z-school"',
}

API_BASE_URL = "https://deadprogrammer.ru/all"
BOOKING_BASE_URL = "https://бигзэтика.рф/book"

# Главное меню
MAIN_MENU_KEYBOARD = [
    [KeyboardButton("Просмотр расписания"), KeyboardButton("Бронировать")],
    [KeyboardButton("❓ Помощь"), KeyboardButton("ℹ️ О боте")]
]

# Меню просмотра расписания больше не используется
