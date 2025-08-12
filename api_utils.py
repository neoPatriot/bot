import requests
import logging

logger = logging.getLogger(__name__)


def fetch_bookings(date_str, api_base_url):
    """Получение данных о бронированиях"""
    try:
        api_url = f"{api_base_url}/{date_str}/"
        logger.info(f"Запрос к API: {api_url}")
        response = requests.get(api_url)

        if response.status_code != 200:
            logger.error(f"API вернул код ошибки: {response.status_code}")
            return None

        try:
            return response.json()
        except Exception as json_error:
            logger.error(f"Ошибка декодирования JSON: {json_error}")
            logger.error(f"Ответ API: {response.text[:500]}...")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API: {e}")
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка при работе с API: {e}")
        return None


def extract_times(times_str):
    """Извлекает временные интервалы"""
    if not times_str:
        return "Время не указано"

    try:
        lines = times_str.split('\r\n')
        time_lines = [line.strip() for line in lines if '-' in line and any(char.isdigit() for char in line)]
        trimmed_lines = [line[:-6] if len(line) >= 6 else line for line in time_lines]
        return '\n'.join(trimmed_lines) if trimmed_lines else "Время не указано"
    except Exception as e:
        logger.error(f"Ошибка извлечения времени: {e}")
        return "Время не указано"


def get_start_time(booking):
    """Извлекает время начала для сортировки"""
    times_str = booking.get('times', '')
    if not times_str:
        return "99:99"  # Поместить бронирования без времени в конец

    try:
        lines = times_str.split('\r\n')
        time_lines = [line.strip() for line in lines if '-' in line and any(char.isdigit() for char in line)]
        if not time_lines:
            return "99:99"

        # Сортируем временные интервалы, чтобы найти самый ранний
        time_lines.sort()

        first_time_range = time_lines[0]
        start_time = first_time_range.split('-')[0]
        return start_time
    except Exception:
        return "99:99"