import requests
from bs4 import BeautifulSoup
import logging
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


def submit_booking(room_id, date_str, selected_slots, user_name, phone_number, comment):
    """
    Submits the booking to the website by navigating to the final form page
    and then sending a POST request with a CSRF token.
    Returns a tuple (success: bool, message: str).
    """
    submit_url = BOOKING_BASE_URL
    time_str = ",".join(selected_slots)
    final_form_url = f"{BOOKING_BASE_URL}?room={room_id}&date={date_str}&time={time_str}"

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
                'name': user_name,
                'phone': phone_number,
                'comment': comment,
                'submit': '',
                # The server likely gets room, date, and time from the session after the previous GET
            }

            logger.info(f"Submitting booking to {submit_url} for room {room_id}")
            post_response = session.post(
                submit_url,
                data=payload,
                headers={'User-Agent': 'TelegramBookingBot/1.0', 'Referer': final_form_url}
            )

            # A successful submission usually redirects
            if post_response.ok and post_response.url != submit_url:
                 logger.info(f"Booking submission successful with status {post_response.status_code}.")
                 return True, "Заявка успешно отправлена!"
            elif post_response.ok and "успешно" in post_response.text.lower():
                 logger.info(f"Booking submission successful with status {post_response.status_code}.")
                 return True, "Заявка успешно отправлена!"
            else:
                logger.error(f"Booking submission failed. Status: {post_response.status_code}, URL: {post_response.url}, Response: {post_response.text[:300]}")
                return False, f"Ошибка при отправке заявки. Сервер ответил со статусом: {post_response.status_code}."

        except requests.exceptions.RequestException as e:
            logger.error(f"A network error occurred during booking submission: {e}")
            return False, f"Произошла сетевая ошибка при отправке заявки."
        except Exception as e:
            logger.error(f"An unexpected error occurred in submit_booking: {e}", exc_info=True)
            return False, "Произошла непредвиденная ошибка при отправке бронирования."