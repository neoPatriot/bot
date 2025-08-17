import requests
from bs4 import BeautifulSoup
import logging
import re
import datetime
from urllib.parse import urljoin
from config import BOOKING_BASE_URL

logger = logging.getLogger(__name__)


def fetch_available_slots(room_id, date_str):
    """Получает доступные временные слоты для бронирования"""
    try:
        params = {'room': room_id, 'date': date_str}
        response = requests.get(BOOKING_BASE_URL, params=params)

        if response.status_code != 200:
            logger.error(f"Ошибка при запросе слотов: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        slots = []

        # Ищем все блоки с доступными слотами
        alert_divs = soup.find_all('div', class_='alert alert-success')

        for alert in alert_divs:
            time_input = alert.find('input', {'name': 'time'})
            if time_input:
                value = time_input.get('value')
                # Получаем текст метки, убирая лишние пробелы
                label_text = alert.get_text(strip=True)
                # Убираем возможные дублирования пробелов
                label_text = ' '.join(label_text.split())
                slots.append((value, label_text))

        return slots

    except Exception as e:
        logger.error(f"Ошибка при получении слотов: {e}")
        return None


def submit_booking(room_id, room_name, date_str, selected_slots, all_slots, user_name, phone_number, comment):
    """
    Submits the booking to the website by navigating to the final form page
    and then sending a POST request with a CSRF token.
    Returns a tuple (success: bool, message: str).
    """
    submit_url = BOOKING_BASE_URL
    time_str_for_get = ",".join(selected_slots)
    final_form_url = f"{BOOKING_BASE_URL}?room={room_id}&date={date_str}&time={time_str_for_get}"

    with requests.Session() as session:
        try:
            # Step 1: GET request to the final form page to get the CSRF token
            logger.info(f"Fetching final booking form from: {final_form_url}")
            get_response = session.get(final_form_url, headers={'User-Agent': 'TelegramBookingBot/1.0'})
            get_response.raise_for_status()

            soup = BeautifulSoup(get_response.text, 'html.parser')
            token_input = soup.find('input', {'name': '_token'})

            if not token_input or not token_input.get('value'):
                logger.error(f"Could not find CSRF token on the final booking page: {final_form_url}")
                logger.error(f"Page content received: {get_response.text[:500]}")
                return False, "Не удалось найти CSRF-токен на финальной странице бронирования. Возможно, выбранные слоты уже заняты."

            csrf_token = token_input.get('value')
            logger.info(f"Found CSRF token on final page: {csrf_token[:10]}...")

            # Find the actual submit URL from the form's action attribute
            form = soup.find('form')
            if form and form.get('action'):
                submit_url = urljoin(BOOKING_BASE_URL, form.get('action'))

            # Step 2: POST request to submit the booking
            payload = {
                '_token': csrf_token,
                'room': room_id,
                'date': date_str,
                'time': time_str_for_get,
                'name': user_name,
                'phone': phone_number,
                'comment': comment,
                'rules': 'on', # This was the missing required field
                'submit': '',
            }

            logger.info(f"Submitting booking to {submit_url} for room {room_id}")
            post_response = session.post(
                submit_url,
                data=payload,
                headers={'User-Agent': 'TelegramBookingBot/1.0', 'Referer': final_form_url}
            )

            # A successful submission contains the phrase "Благодарим за Ваш выбор"
            if post_response.ok and "Благодарим за Ваш выбор" in post_response.text:
                logger.info(f"Booking submission successful with status {post_response.status_code}.")

                # --- Construct the detailed success message ---

                # 1. Format date with Russian names
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    # Define Russian locale names
                    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
                    months = ["", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня", "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"]
                    day_of_week = days[date_obj.weekday()]
                    month_name = months[date_obj.month]
                    formatted_date = f"{day_of_week}, {date_obj.day}, {month_name}, {date_obj.year}"
                except (ValueError, TypeError):
                    formatted_date = date_str # Fallback

                # 2. Find selected slots' labels and calculate total price
                total_price = 0
                selected_labels = []
                for slot_value in selected_slots:
                    for value, label in all_slots:
                        if value == slot_value:
                            selected_labels.append(label)
                            price_match = re.search(r'\(₽(\d+)\)', label)
                            if price_match:
                                total_price += int(price_match.group(1))
                            break

                intervals_text = "\n".join(selected_labels)

                # 3. Construct the final message
                success_message = (
                    f"Уважаемый {user_name}!\n"
                    f"Ваша заявка на {formatted_date}\n"
                    f"Интервалы: {intervals_text}\n"
                    f"Общей стоимостью: ₽ {total_price}\n"
                    f"Зал: {room_name}.\n\n"
                    "ВНИМАНИЕ! При бронировании менее чем за СУТКИ, обязательно свяжитесь с АДМИНИСТРАЦИЕЙ "
                    "по телефону +7-8142-63-53-93 или +7-911-400-53-63 для подтверждения свободного ВРЕМЕНИ! "
                    "При ОТМЕНЕ менее, чем за ДВОЕ суток - неустойка (50% от полной суммы бронирования)!"
                )

                return True, success_message
            else:
                logger.error(f"Booking submission failed. Status: {post_response.status_code}, URL: {post_response.url}, Response: {post_response.text[:300]}")
                return False, f"Ошибка при отправке заявки. Сервер ответил со статусом: {post_response.status_code}."

        except requests.exceptions.RequestException as e:
            logger.error(f"A network error occurred during booking submission: {e}")
            return False, f"Произошла сетевая ошибка при отправке заявки."
        except Exception as e:
            logger.error(f"An unexpected error occurred in submit_booking: {e}", exc_info=True)
            return False, "Произошла непредвиденная ошибка при отправке бронирования."