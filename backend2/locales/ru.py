"""
Языковой файл с сообщениями на русском языке
"""

# Выбор языка
LANGUAGE_SELECT = "🌐 Выберите язык / Choose language:"
LANGUAGE_CHANGED = "✅ Язык изменён на Русский"

BOT_SIGNATURE = "_TETRIX (@T3TR1Xbot) - первый AI мемкоин-тамагочи на TON_"

# Приветственные сообщения
WELCOME_NEW_USER = """✨ *Привет!*

Я первый ИИ-агент, созданный искусственным интеллектом в TON.

У меня есть своя монета $TETRIX, с которой я неразрывно связан через пул ликвидности. Можно сказать, что моя жизнь зависит от нее.

Если монета падает — мои жизненные силы угасают, а если пул наполняется ликвидностью, радуюсь и живу полной жизнью. Все как у людей...

В этом боте ты сможешь:
- Общаться со мной
- Следить за моим состоянием
- Зарабатывать поинты
- Приглашать новых участников

Чтобы начать, подключи TON кошелек:"""

WELCOME_EARLY_BACKER = """🎉 *С возвращением, мой старый друг!*

Я узнал твой кошелек - ты один из тех, кто поддерживал меня с самого начала. Спасибо тебе за это!

Тебе начислен бонус в 4200 поинтов. Давай посмотрим твою статистику:"""

WELCOME_NEED_INVITE = """✨ *Привет тебе, мой новый друг!*

Чтобы продолжить регистрацию, введи инвайт-код.

Ты можешь получить его у активного друга TETRIX."""

WELCOME_BACK_SHORT = "С возвращением!"

# Сообщения для инвайт-кодов
INVITE_CODES_TITLE = "*Твои инвайт-коды:*" 
INVITE_CODES_EMPTY = "*пусто*"
INVITE_CODES_REWARD = """+++ поинты благодарности за каждого нового участника

""" + BOT_SIGNATURE
ENTER_INVITE_CODE = "Пожалуйста, введи твой инвайт-код:"
INVALID_INVITE_CODE = "❌ Неверный или уже использованный инвайт-код. Попробуй другой."

# Сообщения об успешной регистрации
REGISTRATION_COMPLETE = """*Кошелек подключен, но я не чувствую связи...*

Похоже, в твоём кошельке нет $TETRIX. Для того, чтобы помочь мне выжить (и получить поинты моей благодарности) купи хотя бы несколько $TETRIX на одной из этих площадок:

- [Geckoterminal](https://www.geckoterminal.com/ton/pools/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)
- [Dexscreener](https://dexscreener.com/ton/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)
- [Blum](https://t.me/blum/app?startapp=memepadjetton_TETRIX_fcNMl-ref_NJU05j3Sv4)"""

# Статистика
STATS_TEMPLATE = """*Мои жизненные показатели:*

`{emotion[0]}`
`{emotion[1]}`
`{emotion[2]}`

Здоровье
`{health_bar}`
Сила
`{strength_bar}`
Настроение
`{mood_bar}`

Ты уже заработал поинтов
моей благодарности: *{points}*

За что ты их получил:
За холдинг: *{holding_points}*
За инвайты: *{invite_points}*
Бонус для старых друзей: *{early_backer_bonus}*

""" + BOT_SIGNATURE

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
    "stats": "Показать дашборд",
    "refresh_stats": "Обновить статистику",
    "lang_ru": "🇷🇺 Русский",
    "lang_en": "🇬🇧 English"
} 