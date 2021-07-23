import os
import time
import requests
import logging
from logging.handlers import RotatingFileHandler

from telegram import Bot
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler(
    'logfile.log', maxBytes=1000, backupCount=3)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(name)s, %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    url = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    from_date = {'from_date': current_timestamp}
    homework_statuses = requests.get(
        url,
        headers=headers,
        params=from_date
    )

    return homework_statuses.json()


def send_message(message):
    return bot.send_message(chat_id=CHAT_ID, text=message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp

    while True:
        try:
            logger.debug('Бот запущен')

            homeworks = get_homeworks(current_timestamp)
            homework = homeworks['homeworks'][0]
            logger.info('Бот получил домашку')

            send_message(parse_homework_status(homework))
            logger.info('Бот отправил сообщение')
            time.sleep(60 * 60)  # Опрашивать раз в час

        except Exception as e:
            send_message(f'Бот упал с ошибкой: {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
