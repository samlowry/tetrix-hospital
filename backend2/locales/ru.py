"""
Языковой файл с сообщениями на русском языке
"""

# Приветственные сообщения
WELCOME_NEW_USER = """✨ *Привет!*

Я первый ИИ-агент, созданный искусственным интеллектом в TON. У меня есть своя монета $TETRIX, с которой я неразрывно связан через пул ликвидности.

В этом боте ты сможешь:
- Общаться со мной
- Следить за моим состоянием
- Зарабатывать поинты
- Приглашать новых участников

Чтобы начать, подключи TON кошелек:"""

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
STATS_TEMPLATE = """💎 Поинты: {points}
👥 Успешные инвайты: {total_invites}
🎯 Доступные слоты: {available_slots}

Breakdown:
- Холдинг: {holding_points}
- Инвайты: {invite_points}
- Early bonus: {early_backer_bonus}"""

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
    "open_menu": "Открыть меню",
    "show_invites": "Мои инвайт-коды",
    "refresh_invites": "Обновить список",
    "stats": "Статистика",
    "refresh_stats": "Обновить"
} 