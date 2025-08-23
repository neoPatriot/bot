from telegram.ext import Application, PicklePersistence
import logging
from handlers import setup_handlers
from config import TOKEN

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    try:
        # Создаем объект persistence
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")

        # Создаем приложение с persistence
        app = Application.builder().token(TOKEN).persistence(persistence).build()

        setup_handlers(app)
        logger.info("Бот запущен и ожидает сообщений...")
        app.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    main()