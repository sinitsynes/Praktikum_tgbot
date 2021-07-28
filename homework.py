import logging
import os
import sys
import time
from json.decoder import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

# Настройка логгера
log_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'logfile.log')
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(
    log_path, maxBytes=1000, backupCount=3)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s, %(levelname)s, %(message)s',
                    handlers=[file_handler, console_handler])

# Проверка токенов
try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except Exception as e:
    token_error = f'Ошибка с токеном {e}.'
    logging.exception(token_error)
    sys.exit('Бот остановлен, нет токена')

URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
AUTH_HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Ревьюеру всё понравилось, работа зачтена!',
    'rejected': 'К сожалению, в работе нашлись ошибки.',
    'reviewing': 'Она проходит ревью'
}

TIME_SLEEP = 20 * 60

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    if homework_name is None:
        name_error = 'Сервер не вернул название работы'
        logging.error(name_error)
        return name_error

    homework_status = homework.get('status')
    if homework_status not in dict(HOMEWORK_STATUSES):
        unknown_status = HOMEWORK_STATUSES.get(
            homework_status, 'Неизвестный статус')
        status_error = f'Сервер не вернул статус работы: {unknown_status}'
        logging.error(status_error)
        return status_error
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    if current_timestamp is None or 0:
        current_timestamp = int(time.time()) - TIME_SLEEP

    from_date = {'from_date': current_timestamp}

    try:
        homework_statuses = requests.get(
            URL,
            headers=AUTH_HEADERS,
            params=from_date
        )
        status_code = homework_statuses.status_code
        return homework_statuses.json()

    except status_code != 200:
        http_error = f'Неверный статус ответа сервера: {status_code}'
        logging.error(http_error)
        send_message(http_error)
        sys.exit(f'Бот остановлен из-за ошибки: {http_error}')

    except Exception as e:
        exception_error = f'Проблема в get_homeworks(), {e}'
        logging.exception(exception_error)
        send_message(exception_error)
        sys.exit(f'Бот остановлен из-за ошибки: {exception_error}')


def send_message(message):
    return bot.send_message(chat_id=CHAT_ID, text=message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp
    logging.debug('Бот запущен')

    BOT_ERROR = 'Бот упал с ошибкой:'

    while True:
        try:
            homeworks = get_homeworks(current_timestamp)
            homeworks_list = homeworks.get('homeworks')
            homework = homeworks_list[0]
            message = parse_homework_status(homework)
            send_message(message)
            logging.info(f'Бот отправил сообщение {message}')
            # Обновляем время проверки домашки
            current_date = homeworks.get('current_date')
            current_timestamp = current_date
            time.sleep(TIME_SLEEP)

        except IndexError:
            logging.info('Новой домашки нет')
            # Опрашивать раз в двадцать минут, ограничение Heroku
            time.sleep(TIME_SLEEP)

        except JSONDecodeError:
            decode_error_message = 'Ошибка декодирования JSON в ответе сервера'
            logging.error(decode_error_message)
            send_message(decode_error_message)
            sys.exit(decode_error_message)

        except Exception as e:
            logging.exception(f'{BOT_ERROR} {e}')
            send_message(f'{BOT_ERROR} {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
