import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

# Настройка логгера
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(name)s, %(message)s')
log_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'logfile.log')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(
    log_path, maxBytes=1000, backupCount=3)
file_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO,
                    handlers=[file_handler, console_handler])
logging_error = 'Неверный ответ сервера'

# Токены авторизаций
PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
AUTH_HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}

token_check = {
    PRAKTIKUM_TOKEN: 'PRAKTIKUM_TOKEN',
    TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
    CHAT_ID: 'TELEGRAM_CHAT_ID'}

for token, value in token_check.items():
    try:
        token = os.environ[value]
    except token is None:
        logging.error(f'Токен авторизации {token} недоступен')

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('Сервер не вернул название работы')
        bot.send_message(chat_id=CHAT_ID, text=logging.error)

    homework_statuses = {
        'approved': 'Ревьюеру всё понравилось, работа зачтена!',
        'rejected': 'К сожалению, в работе нашлись ошибки.',
        'reviewing': 'Она проходит ревью'
    }

    homework_status = homework.get('status')

    if homework_status not in list(homework_statuses):
        logging.error('Сервер не вернул статус работы')
        bot.send_message(chat_id=CHAT_ID, text=logging.error)

    verdict = homework_statuses[homework_status]
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    url = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
    if current_timestamp is None:
        current_timestamp = 0
    from_date = {'from_date': current_timestamp}

    try:
        homework_statuses = requests.get(
            url,
            headers=AUTH_HEADERS,
            params=from_date
        )
        return homework_statuses.json()
    except Exception:
        logging.exception(logging_error)
        bot.send_message(
            chat_id=CHAT_ID,
            text=f'Проблема в get_homeworks(), {logging.error}')


def send_message(message):
    logging.info(f'Бот отправил сообщение {message}')
    return bot.send_message(chat_id=CHAT_ID, text=message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp
    logging.debug('Бот запущен')

    bot_error = 'Бот упал с ошибкой:'

    while True:
        try:
            homeworks = get_homeworks(current_timestamp)
            try:
                homework = homeworks['homeworks'][0]
                logging.info('Бот получил домашку')
                message = parse_homework_status(homework)
                send_message(message)
                # Обновляем время проверки домашки
                date_updated = homework.get('date_updated')
                structured_date = time.strptime(
                    date_updated, '%Y-%m-%dT%H:%M:%SZ')
                current_timestamp = time.mktime(structured_date)
            except IndexError:
                logging.info('Новой домашки нет')
            # Опрашивать раз в двадцать минут, ограничение Heroku
            time.sleep(20 * 60)

        except Exception as e:
            logging.exception(f'{bot_error} {e}')
            send_message(f'{bot_error} {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
