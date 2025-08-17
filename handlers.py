from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
import datetime
import asyncio
import logging
from keyboards import generate_room_selection, generate_calendar
from api_utils import fetch_bookings, extract_times, get_start_time
from booking_utils import fetch_available_slots, submit_booking
from config import ROOM_NAMES, ADMIN_USER_IDS, ROOM_ADMINS, API_BASE_URL, MAIN_MENU_KEYBOARD, BOOKING_BASE_URL

# Инициализация логгера
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler (бронирование)
(
    BOOKING_ROOM,
    BOOKING_DATE,
    BOOKING_SLOTS,
    GET_NAME,
    GET_PHONE,
    GET_COMMENT
) = range(4, 10)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        await update.message.reply_text(
            "👋 Добро пожаловать в бот бронирования bigZ!\n"
            "Выберите действие из меню ниже:",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True,
                one_time_keyboard=False
            )
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.lower()

    if text == "просмотр расписания":
        await show_room_selection(update, context, "view")
    elif text == "⬅️ назад в главное меню":
        await show_main_menu(update, context)
    elif text == "❓ помощь":
        await show_help(update, context)
    elif text == "ℹ️ о боте":
        await show_about(update, context)
    elif text == "отмена":
        await cancel_booking_command(update, context)
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Используйте меню ниже ⬇️",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню"""
    if isinstance(update, CallbackQuery):
        await update.edit_message_text(
            "Главное меню:",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )


async def show_booking_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню бронирования (выбор зала)"""
    if isinstance(update, CallbackQuery):
        await update.edit_message_text(
            "🏢 Выберите зал для бронирования:",
            reply_markup=generate_room_selection(ROOM_NAMES, prefix="book_room_")
        )
    else:
        await update.message.reply_text(
            "🏢 Выберите зал для бронирования:",
            reply_markup=generate_room_selection(ROOM_NAMES, prefix="book_room_")
        )
    return BOOKING_ROOM


async def show_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, purpose="view"):
    """Показывает выбор залов для просмотра расписания"""
    try:
        prefix = "select_room_"
        if purpose == "booking":
            prefix = "book_room_"

        if isinstance(update, CallbackQuery):
            await update.edit_message_text(
                "🏢 Выберите зал:",
                reply_markup=generate_room_selection(ROOM_NAMES, prefix=prefix)
            )
        else:
            await update.message.reply_text(
                "🏢 Выберите зал:",
                reply_markup=generate_room_selection(ROOM_NAMES, prefix=prefix)
            )
    except Exception as e:
        logger.error(f"Ошибка при показе выбора залов: {e}")
        reply_markup = ReplyKeyboardMarkup(
            SCHEDULE_MENU_KEYBOARD if purpose == "view" else MAIN_MENU_KEYBOARD,
            resize_keyboard=True
        )

        if isinstance(update, CallbackQuery):
            await update.edit_message_text("⚠️ Не удалось открыть выбор залов", reply_markup=reply_markup)
        else:
            await update.message.reply_text("⚠️ Не удалось открыть выбор залов", reply_markup=reply_markup)


async def show_calendar(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        selected_room,
        user_id,
        year=None,
        month=None,
        purpose="view"  # 'view' или 'booking'
):
    """Показывает календарь с учетом выбранного зала"""
    try:
        now = datetime.datetime.now()
        year = year or now.year
        month = month or now.month

        text = "📅 Выберите дату"
        if purpose == "view":
            text += " для просмотра расписания"
        else:
            text += " для бронирования"

        if selected_room and selected_room != "all":
            room_name = ROOM_NAMES.get(int(selected_room), selected_room)
            text += f" зала {room_name}"

        reply_markup = generate_calendar(
            year=year,
            month=month,
            selected_room=selected_room,
            user_id=user_id,
            room_names=ROOM_NAMES,
            admin_ids=ADMIN_USER_IDS,
            room_admins=ROOM_ADMINS,
            purpose=purpose
        )

        if isinstance(update, Update) and update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif isinstance(update, CallbackQuery):
            await update.edit_message_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при показе календаря: {e}")
        if isinstance(update, Update) and update.message:
            await update.message.reply_text("⚠️ Не удалось открыть календарь")
        elif isinstance(update, CallbackQuery):
            await update.answer("⚠️ Не удалось открыть календарь")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    help_text = (
        "ℹ️ **Помощь по использованию бота**\n\n"
        "1. Используйте кнопку \"Просмотр расписания\" для просмотра занятости помещений\n"
        "2. Затем выберите зал и дату в календаре\n"
        "3. Бот покажет все бронирования на выбранную дату\n"
        "4. Для навигации по месяцам используйте кнопки \"⬅️\" и \"➡️\"\n\n"
        "**Бронирование:**\n"
        "- Выберите пункт \"Бронировать\", затем зал, дату и доступные слоты\n"
        "- После выбора слотов вы получите ссылку для оформления брони на сайте\n\n"
        "Если у вас остались вопросы, обратитесь к администратору."
    )

    if isinstance(update, CallbackQuery):
        await update.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о боте"""
    about_text = (
        "🤖 **Информация о боте**\n\n"
        "Этот бот позволяет просматривать бронирования помещений bigZ и начинать процесс бронирования.\n\n"
        "**Текущие функции:**\n"
        "- Просмотр расписания бронирований\n"
        "- Фильтрация по залам\n"
        "- Просмотр деталей бронирования\n"
        "- Выбор слотов для бронирования и получение ссылки на оформление\n\n"
        "Версия: 2.0\n"
        "Разработчик: Леший\n"
    )

    if isinstance(update, CallbackQuery):
        await update.edit_message_text(
            about_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            about_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                MAIN_MENU_KEYBOARD,
                resize_keyboard=True
            )
        )


async def handle_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """Обработчик инлайн-кнопок (для просмотра расписания)"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    try:
        if data.startswith("select_room_"):
            room_selection = data.split("_")[2]
            context.user_data['selected_room'] = room_selection
            await show_calendar(
                query,
                context,
                room_selection,
                user_id,
                purpose="view"
            )

        elif data.startswith("select_"):
            parts = data.split("_")
            year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
            selected_room = context.user_data.get('selected_room', 'all')

            is_admin = user_id in ADMIN_USER_IDS or any(
                user_id in ROOM_ADMINS.get(rid, [])
                for rid in ROOM_ADMINS
            )
            selected_date = datetime.datetime(year, month, day)

            if not is_admin and selected_date.date() < datetime.datetime.now().date():
                await query.edit_message_text("⚠️ Вы не можете просматривать прошедшие даты")
                return

            date_str = f"{year}{month:02d}{day:02d}"
            await query.edit_message_text(f"⏳ Ищу бронирования на {day}.{month}.{year}...")
            bookings = fetch_bookings(date_str, API_BASE_URL)

            if bookings is None:
                await query.edit_message_text("❌ Не удалось получить данные с сервера. Попробуйте позже.")
                return

            await send_bookings(
                context,
                query.message.chat_id,
                bookings,
                user_id,
                selected_room
            )

        elif data.startswith("prev_") or data.startswith("next_"):
            parts = data.split("_")
            year, month = int(parts[1]), int(parts[2])
            selected_room = parts[3] if len(parts) > 3 else None
            if selected_room:
                context.user_data['selected_room'] = selected_room

            purpose = "view"
            if len(parts) > 4 and parts[4] == "book":
                purpose = "booking"

            await show_calendar(
                query,
                context,
                selected_room,
                user_id,
                year,
                month,
                purpose
            )

    except Exception as e:
        logger.error(f"Ошибка в handle_callback: {e}", exc_info=True)
        try:
            await query.edit_message_text("⚠️ Произошла ошибка при обработке запроса")
        except:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ Произошла ошибка при обработке запроса"
            )


async def send_bookings(
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        bookings: list,
        user_id: int,
        selected_room: str
):
    """Отправляет информацию о бронированиях с учетом прав доступа"""
    try:
        if selected_room and selected_room != "all":
            bookings = [b for b in bookings if str(b.get('room_id')) == selected_room]

        is_global_admin = user_id in ADMIN_USER_IDS
        is_room_admin = any(
            user_id in ROOM_ADMINS.get(b.get('room_id'), [])
            for b in bookings
        )

        if not bookings:
            if not selected_room or selected_room == "all":
                room_text = "во всех залах"
            else:
                room_name = ROOM_NAMES.get(int(selected_room), f"зале {selected_room}")
                room_text = f"в {room_name}"

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📭 На выбранную дату {room_text} бронирований не найдено."
            )
            return

        bookings_by_room = {}
        for booking in bookings:
            room_id = booking.get('room_id')
            if room_id not in bookings_by_room:
                bookings_by_room[room_id] = []
            bookings_by_room[room_id].append(booking)

        total_count = len(bookings)
        room_count = len(bookings_by_room)

        if selected_room and selected_room != "all":
            room_name = ROOM_NAMES.get(int(selected_room), f"зал {selected_room}")
            header = f"📋 Найдено {total_count} бронирований в {room_name}:"
        else:
            header = f"📋 Найдено {total_count} бронирований в {room_count} залах:"

        await context.bot.send_message(chat_id=chat_id, text=header)

        for room_id, room_bookings in sorted(bookings_by_room.items()):
            room_name = ROOM_NAMES.get(room_id, f"Зал {room_id}")
            is_current_room_admin = user_id in ROOM_ADMINS.get(room_id, [])

            room_header = f"\n🚪 {room_name} ({len(room_bookings)} бронир.)"
            if is_global_admin or is_current_room_admin:
                room_header += " 👑"

            await context.bot.send_message(chat_id=chat_id, text=room_header)

            sorted_room_bookings = sorted(room_bookings, key=get_start_time)

            for i, booking in enumerate(sorted_room_bookings, 1):
                try:
                    status = str(booking.get('status', '')).lower()
                    is_cancelled = 'cancel' in status
                    show_details = is_global_admin or is_current_room_admin

                    message_parts = []

                    if is_cancelled:
                        message_parts.append("🟨🟨🟨 [ОТМЕНЕНО] 🟨🟨🟨")

                    message_parts.append(f"#{i}: {booking.get('name', 'Без имени')}")

                    if show_details:
                        message_parts.append(f"📞: {booking.get('phone', 'Не указан')}")

                    times = extract_times(booking.get('times', ''))
                    if times:
                        message_parts.append(f"🕒: {times}")

                    message_parts.append(f"Статус: {status.capitalize()}")

                    if show_details and booking.get('comment'):
                        message_parts.append(f"💬: {booking['comment']}")

                    if is_cancelled:
                        message_parts.append("🟨🟨🟨 ОТМЕНЕНО 🟨🟨🟨")

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="\n".join(message_parts)
                    )

                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error(f"Ошибка при отправке бронирования: {e}")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Ошибка при отображении бронирования #{i}"
                    )

    except Exception as e:
        logger.error(f"Критическая ошибка в send_bookings: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Произошла ошибка при формировании списка бронирований"
        )


# Обработчики для процесса бронирования
async def handle_booking_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор зала для бронирования"""
    query = update.callback_query
    await query.answer()

    room_id = int(query.data.split("_")[2])
    # Сохраняем room_id для последующего использования
    context.user_data['booking_room_id'] = room_id
    context.user_data['booking_room_name'] = ROOM_NAMES.get(room_id, f"Зал {room_id}")

    # Показываем календарь для выбора даты бронирования
    await show_calendar(
        query,
        context,
        selected_room=str(room_id),
        user_id=query.from_user.id,
        purpose="booking"
    )
    return BOOKING_DATE


async def handle_booking_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор даты для бронирования"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])

    # Сохраняем дату в формате YYYY-MM-DD
    booking_date = f"{year}-{month:02d}-{day:02d}"
    context.user_data['booking_date'] = booking_date

    room_id = context.user_data['booking_room_id']
    room_name = context.user_data['booking_room_name']

    await query.edit_message_text(
        f"⏳ Проверяю доступные слоты для {room_name} на {day}.{month}.{year}..."
    )

    # Получаем доступные слоты
    slots = fetch_available_slots(room_id, booking_date)

    if not slots:
        await query.edit_message_text(
            f"❌ На {day}.{month}.{year} в {room_name} нет доступных слотов для бронирования.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Выбрать другую дату", callback_data=f"book_retry_date_{room_id}")]
            ])
        )
        return BOOKING_DATE

    # Сохраняем слоты
    context.user_data['booking_slots'] = slots
    context.user_data['selected_slots'] = []

    # Показываем доступные слоты
    await show_booking_slots(query, context)
    return BOOKING_SLOTS


async def show_booking_slots(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показывает доступные слоты для бронирования"""
    room_name = context.user_data['booking_room_name']
    booking_date = context.user_data['booking_date']
    slots = context.user_data['booking_slots']
    selected_slots = context.user_data.get('selected_slots', [])

    # Форматируем дату для отображения
    day, month, year = booking_date.split('-')[2], booking_date.split('-')[1], booking_date.split('-')[0]

    text = (
        f"🕒 Выберите временные слоты для бронирования:\n"
        f"🏢 Зал: {room_name}\n"
        f"📅 Дата: {day}.{month}.{year}\n\n"
        f"Доступные слоты:"
    )

    # Создаем клавиатуру с кнопками слотов
    keyboard = []
    for value, label in slots:
        # Помечаем выбранные слоты
        prefix = "✅ " if value in selected_slots else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{label}",
                callback_data=f"slot_toggle_{value}"
            )
        ])

    # Кнопки подтверждения и возврата
    action_buttons = []
    if selected_slots:
        action_buttons.append(InlineKeyboardButton("📝 Подтвердить выбор", callback_data="slots_confirm"))

    action_buttons.append(InlineKeyboardButton("🔄 Выбрать другую дату", callback_data="book_retry_date"))
    action_buttons.append(InlineKeyboardButton("❌ Отменить бронирование", callback_data="cancel_booking"))

    keyboard.append(action_buttons)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_slot_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор/отмену слота"""
    query = update.callback_query
    await query.answer()

    slot_value = query.data.split("_", 2)[2]
    selected_slots = context.user_data['selected_slots']

    # Добавляем или удаляем слот
    if slot_value in selected_slots:
        selected_slots.remove(slot_value)
    else:
        selected_slots.append(slot_value)

    # Обновляем сообщение с новым состоянием
    await show_booking_slots(query, context)
    return BOOKING_SLOTS


async def handle_slots_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждает выбор слотов и запрашивает имя."""
    query = update.callback_query
    await query.answer()

    # Проверяем, что слоты выбраны
    if not context.user_data.get('selected_slots'):
        await query.edit_message_text(
            "⚠️ Вы не выбрали ни одного слота. Пожалуйста, выберите хотя бы один."
        )
        # Возвращаемся к выбору слотов, не меняя клавиатуру
        return BOOKING_SLOTS

    text = "📝 Отлично! Теперь, пожалуйста, введите ваше имя или название команды."

    # Отправляем новое сообщение, так как edit_message_text не всегда подходит для смены контекста
    await query.edit_message_text(text)

    return GET_NAME


async def handle_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет имя и запрашивает номер телефона."""
    user_name = update.message.text
    context.user_data['booking_name'] = user_name

    text = f"Отлично, {user_name}! Теперь, пожалуйста, введите ваш номер телефона."
    await update.message.reply_text(text)

    return GET_PHONE


async def handle_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет номер телефона и запрашивает комментарий."""
    phone_number = update.message.text
    # TODO: Добавить валидацию номера телефона
    context.user_data['booking_phone'] = phone_number

    text = "Спасибо! Теперь введите комментарий к вашей заявке или нажмите 'Пропустить', если комментариев нет."
    keyboard = [[InlineKeyboardButton("Пропустить", callback_data="skip_comment")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)

    return GET_COMMENT


def clear_booking_data(context: ContextTypes.DEFAULT_TYPE):
    """Clears all booking-related data from user_data."""
    keys_to_clear = [
        'booking_room_id', 'booking_room_name', 'booking_date',
        'booking_slots', 'selected_slots', 'booking_name',
        'booking_phone', 'booking_comment', 'selected_room'
    ]
    for key in keys_to_clear:
        context.user_data.pop(key, None)

async def finalize_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calls the submission function and informs the user of the result."""
    chat_id = update.effective_chat.id

    # Show a "submitting" message
    submitting_text = "✅ Заявка собрана! Отправляю на сайт..."
    if isinstance(update, CallbackQuery):
        await update.edit_message_text(text=submitting_text)
    else:
        await update.message.reply_text(text=submitting_text)

    # Submit the booking
    success, message = submit_booking(
        room_id=context.user_data.get('booking_room_id'),
        date_str=context.user_data.get('booking_date'),
        selected_slots=context.user_data.get('selected_slots', []),
        user_name=context.user_data.get('booking_name', 'Не указано'),
        phone_number=context.user_data.get('booking_phone', 'Не указан'),
        comment=context.user_data.get('booking_comment', 'Нет')
    )

    # Send the final status as a new message
    final_message = f"✅ {message}" if success else f"❌ {message}"
    await context.bot.send_message(chat_id=chat_id, text=final_message)

    # Clean up and end
    clear_booking_data(context)
    return ConversationHandler.END

async def handle_get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the comment from text and finalizes the booking."""
    context.user_data['booking_comment'] = update.message.text
    return await finalize_booking(update, context)

async def handle_skip_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves an empty comment and finalizes the booking."""
    query = update.callback_query
    await query.answer()
    context.user_data['booking_comment'] = "Пропущено"
    # Pass the query to the finalize function so it can edit the message
    return await finalize_booking(query, context)


async def handle_retry_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторный выбор даты для бронирования"""
    query = update.callback_query
    await query.answer()

    room_id = context.user_data.get('booking_room_id')
    if not room_id:
        # Если room_id не сохранен, начинаем сначала
        await show_booking_menu(query, context)
        return BOOKING_ROOM

    # Показываем календарь снова
    await show_calendar(
        query,
        context,
        selected_room=str(room_id),
        user_id=query.from_user.id,
        purpose="booking"
    )
    return BOOKING_DATE


async def cancel_booking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel"""
    clear_booking_data(context)
    await update.message.reply_text(
        "❌ Бронирование отменено",
        reply_markup=ReplyKeyboardMarkup(
            MAIN_MENU_KEYBOARD,
            resize_keyboard=True
        )
    )
    return ConversationHandler.END


async def cancel_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены бронирования через callback"""
    query = update.callback_query
    await query.answer()

    clear_booking_data(context)

    await query.edit_message_text("❌ Бронирование отменено")
    await show_main_menu(query, context)
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)


def setup_handlers(app):
    """Регистрация обработчиков"""
    # Сначала регистрируем обработчик ошибок
    app.add_error_handler(error_handler)

    # Обработчик команды /start
    app.add_handler(CommandHandler("start", start))

    # Сначала регистрируем ConversationHandler для бронирования
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'(?i)^бронировать$'), show_booking_menu)
        ],
        states={
            BOOKING_ROOM: [
                CallbackQueryHandler(handle_booking_room, pattern=r'^book_room_\d+$')
            ],
            BOOKING_DATE: [
                CallbackQueryHandler(handle_booking_date, pattern=r'^select_\d+_\d+_\d+_?\d*_book$')
            ],
            BOOKING_SLOTS: [
                CallbackQueryHandler(handle_slot_toggle, pattern=r'^slot_toggle_.+$'),
                CallbackQueryHandler(handle_slots_confirm, pattern=r'^slots_confirm$'),
                CallbackQueryHandler(handle_retry_date, pattern=r'^book_retry_date$'),
                CallbackQueryHandler(cancel_booking_callback, pattern=r'^cancel_booking$')
            ],
            GET_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_get_name)
            ],
            GET_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_get_phone)
            ],
            GET_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_get_comment),
                CallbackQueryHandler(handle_skip_comment, pattern=r'^skip_comment$')
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_booking_command),
            MessageHandler(filters.Regex(r'^Отмена$'), cancel_booking_command)
        ],
        per_message=False,
        per_user=True,
        allow_reentry=True
    )
    app.add_handler(conv_handler)

    # Обработчик текстовых сообщений (после ConversationHandler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Затем регистрируем глобальный обработчик инлайн-кнопок для просмотра расписания
    app.add_handler(CallbackQueryHandler(handle_callback))