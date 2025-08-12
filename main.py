from telegram.ext import Application
import logging
from handlers import setup_handlers
from config import TOKEN

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    try:
        app = Application.builder().token(TOKEN).build()
        setup_handlers(app)
        logger.info("Бот запущен и ожидает сообщений...")
        app.run_polling()

    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    main()