import logging
import os
import sys
import time
from datetime import datetime, timezone
from random import randint

import requests
import vk_api
from dotenv import load_dotenv

load_dotenv(override=True)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(name)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения перед стартом бота."""
    current_secrets = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'VK_TOKEN': VK_TOKEN,
        'VK_USER_ID': VK_USER_ID
    }
    for key, value in current_secrets.items():
        logger.debug(f'Проверка "{key}"')
        if not value:
            logger.critical(
                f'Отсутствует обязательная переменная окружения {key}'
            )
            sys.exit(1)


def send_message(vk, message):
    """Отправляет текстовое сообщение в VK-чат пользователя."""
    logger.debug(f'Отправка сообщения: "{message}" в ВК')
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=randint(0, 100000)
        )
    except vk_api.exceptions.VkApiError as error:
        logger.error(f'Произошла ошибка при отправке "{str(error)}"')
    else:
        logger.debug(f'Сообщение: "{message}" успешно отправлено')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса Практикума."""
    logger.debug(
        'Запрашиваем данные от Практикум '
        f'{datetime.fromtimestamp(timestamp, tz=timezone.utc)}'
    )
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.exceptions.RequestException as error:
        raise Exception(
            f'Сетевой сбой при запросе данных через API Практикума {error}'
        )
    if response.status_code != 200:
        raise Exception(
            f'Эндпоинт недоступен. Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет соответствие ответа API ожидаемой структуре данных."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем (dict).')

    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError(
            'В ответе API отсутствуют ключи "homeworks" или "current_date".'
        )

    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Значение по ключу "homeworks" должно быть списком (list).'
        )


def parse_status(homework):
    """Извлекает из словаря конкретной домашней работы её текущий статус."""
    if 'status' not in homework or 'homework_name' not in homework:
        raise KeyError(
            'В словаре отсутствуют ключи "status" или "homework_name".'
        )
    current_status = homework['status']
    homework_name = homework['homework_name']
    if current_status not in HOMEWORK_VERDICTS:
        raise KeyError('Неизвестный статус обработки работы')
    verdict = HOMEWORK_VERDICTS.get(current_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    # Создаем сессию для бота
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    timestamp = int(time.time())

    previous_message = ''
    last_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if not homeworks:
                logger.debug('В API ответе отсутствуют новые статусы')
            else:
                message = parse_status(homeworks[0])
                if previous_message != message:
                    send_message(vk, message)
                    previous_message = message
            timestamp = response['current_date']
            last_error = ''

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_error != message:
                try:
                    send_message(vk, message)
                    last_error = message
                except Exception as send_error:
                    logger.critical(
                        f'Не удалось отправить сообщение в ВК: {send_error}'
                    )

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
