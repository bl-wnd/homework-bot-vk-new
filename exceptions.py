"""Кастомные исключения для проекта Бот-ассистент."""


class PracticumAPIError(Exception):
    """Ошибка при ответе API Практикума (статус-код отличен от 200)."""
    pass


class PracticumNetworkError(Exception):
    """Сетевая ошибка при запросе к API Практикума."""
    pass