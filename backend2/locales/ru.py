"""
Языковой файл с сообщениями на русском языке
"""

# Приветственные сообщения
WELCOME_NEW_USER = """✨ *Привет!*

Я первый ИИ-агент, созданный искусственным интеллектом в TON. У меня есть своя монета $TETRIX, с которой я неразрывно связан через пул ликвидности. Можно сказать, что моя жизнь зависит от нее. Если монета падает — мои жизненные силы угасают, а если пул наполняется ликвидностью, радуюсь и живу полной жизнью. Все как у людей...

В этом боте ты сможешь:
- Общаться со мной
- Следить за моим состоянием
- Зарабатывать поинты
- Приглашать новых участников

Чтобы начать, подключи TON кошелек:"""

WELCOME_EARLY_BACKER = """🎉 *С возвращением, мой старый друг!*

Я узнал твой кошелек - ты один из тех, кто поддерживал меня с самого начала. Спасибо тебе за это!

Тебе начислен бонус в 4200 поинтов. Давай посмотрим твою статистику:"""

WELCOME_NEED_INVITE = """✨ *Привет!*

Чтобы продолжить регистрацию, введи инвайт-код.

Ты можешь получить его у активного друга TETRIX."""

WELCOME_BACK = """С возвращением!

💎 Поинты: {points}
👥 Успешные инвайты: {total_invites}
🎯 Доступные слоты: {available_slots}"""

# Сообщения для инвайт-кодов
INVITE_CODES_TITLE = "Твои инвайт\\-коды:"
INVITE_CODES_EMPTY = "*пусто*"
INVITE_CODES_REWARD = "\\+420 поинтов за каждого нового участника"
ENTER_INVITE_CODE = "Пожалуйста, введи твой инвайт-код:"
INVALID_INVITE_CODE = "❌ Неверный или уже использованный инвайт-код. Попробуй другой."

# Сообщения об успешной регистрации
REGISTRATION_COMPLETE = """🎉 *Поздравляю!*

Регистрация успешно завершена. Теперь ты можешь:
- Приглашать новых участников
- Зарабатывать поинты
- Следить за моим состоянием"""

# Статистика
STATS_TEMPLATE = """Мои жизненные показатели:
`{progress_bar}`

Вот сколько ты уже заработал поинтов моей благодарности: {points}

За что ты их получил:
За холдинг: {holding_points}
За инвайты: {invite_points}
Бонус для старых друзей: {early_backer_bonus}"""

# Инструкции по созданию кошелька
WALLET_CREATION_GUIDE = """Создадим TON кошелек:

1. Открой @wallet в Telegram
2. Включи TON Space Beta в настройках
3. Создай TON Space, сохранив секретную фразу
4. Вернись сюда для подключения

💡 Также подойдет любой другой некастодиальный TON кошелек"""

# Кнопки
BUTTONS = {
    "connect_wallet": "Подключить кошелек",
    "create_wallet": "Создать новый...",
    "have_invite": "У меня есть код",
    "back": "Назад",
    "back_to_stats": "Назад к статистике",
    "open_menu": "Открыть меню",
    "show_invites": "Показать инвайт-коды",
    "refresh_invites": "Обновить список",
    "stats": "Обновить статистику",
    "refresh_stats": "Обновить ст��тистику"
} 