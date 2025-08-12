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