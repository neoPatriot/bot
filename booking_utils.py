import requests
from bs4 import BeautifulSoup
import logging
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


def submit_booking(room_id, date_str, selected_slots, user_name, phone_number, comment):
    """
    Submits the booking to the website by handling CSRF tokens.
    Returns a tuple (success: bool, message: str).
    """
    # The page with the form is the same as the one for fetching slots
    form_page_url = f"{BOOKING_BASE_URL}?room={room_id}&date={date_str}"
    submit_url = BOOKING_BASE_URL  # The form posts to the same base URL

    with requests.Session() as session:
        try:
            # 1. GET request to get the CSRF token and session cookie
            logger.info(f"Fetching booking page to get CSRF token: {form_page_url}")
            get_response = session.get(form_page_url, headers={'User-Agent': 'TelegramBookingBot/1.0'})
            get_response.raise_for_status()

            soup = BeautifulSoup(get_response.text, 'html.parser')
            token_input = soup.find('input', {'name': '_token'})

            if not token_input or not token_input.get('value'):
                logger.error("Could not find CSRF token on the booking page.")
                return False, "Не удалось получить CSRF-токен для отправки формы."

            csrf_token = token_input.get('value')
            logger.info(f"Found CSRF token: {csrf_token[:10]}...")

            # 2. POST request to submit the booking
            payload = {
                '_token': csrf_token,
                'room_id': room_id,
                'date': date_str,
                'time': selected_slots,  # requests will handle this as multiple 'time' keys
                'name': user_name,
                'phone': phone_number,
                'comment': comment,
                'submit': '' # Often forms have a submit button with a name
            }
            logger.info(f"Submitting booking with payload for room {room_id}")

            post_response = session.post(
                submit_url,
                data=payload,
                headers={'User-Agent': 'TelegramBookingBot/1.0'}
            )

            # A redirect (302) or a 200 with a success message usually means success
            if post_response.status_code == 302 or (post_response.status_code == 200 and "успешно" in post_response.text.lower()):
                 logger.info(f"Booking submission successful with status {post_response.status_code}.")
                 # We can check the redirect location header if needed
                 # location = post_response.headers.get('Location')
                 return True, "Заявка успешно отправлена!"
            else:
                logger.error(f"Booking submission failed. Status: {post_response.status_code}, Response: {post_response.text[:300]}")
                return False, f"Ошибка при отправке заявки. Сервер ответил со статусом: {post_response.status_code}."

        except requests.exceptions.RequestException as e:
            logger.error(f"A network error occurred during booking submission: {e}")
            return False, f"Произошла сетевая ошибка при отправке заявки."
        except Exception as e:
            logger.error(f"An unexpected error occurred in submit_booking: {e}")
            return False, "Произошла непредвиденная ошибка при отправке бронирования."