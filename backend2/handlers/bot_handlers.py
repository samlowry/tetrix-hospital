from ..locales.i18n import with_locale

class BotHandlers:
    def __init__(self, user_service):
        self.user_service = user_service

    @with_locale
    async def send_welcome(self, strings, telegram_id: int):
        """
        strings будет автоматически содержать правильный языковой модуль
        в зависимости от языка пользователя
        """
        return strings.WELCOME_MESSAGE

    @with_locale
    async def show_stats(self, strings, user):
        """
        Работает и с объектом пользователя, который имеет telegram_id
        """
        return strings.STATS_MESSAGE 