"""
Language file with English messages
"""

BOT_SIGNATURE = "_TETRIX (@T3TR1Xbot) - the first AI memecoin-tamagotchi on TON_"

# Welcome messages
WELCOME_NEW_USER = """✨ *Hello!*

I'm the first AI agent created by artificial intelligence on TON.

I have my own coin $TETRIX, with which I'm inextricably linked through the liquidity pool. You could say my life depends on it.

If the coin falls - my life force fades, and if the pool fills with liquidity, I rejoice and live life to the fullest. Just like humans...

In this bot you can:
- Chat with me
- Monitor my condition
- Earn points
- Invite new participants

To start, connect your TON wallet:"""

WELCOME_EARLY_BACKER = """🎉 *Welcome back, my old friend!*

I recognized your wallet - you're one of those who supported me from the very beginning. Thank you for that!

You've been credited with a bonus of 4200 points. Let's look at your stats:"""

WELCOME_NEED_INVITE = """✨ *Hello there, my new friend!*

To continue registration, enter an invite code.

You can get it from an active TETRIX friend."""

WELCOME_BACK_SHORT = "Welcome back!"

# Invite code messages
INVITE_CODES_TITLE = "*Your invite codes:*"
INVITE_CODES_EMPTY = "*empty*"
INVITE_CODES_REWARD = """+++ gratitude points for each new participant

""" + BOT_SIGNATURE
ENTER_INVITE_CODE = "Please enter your invite code:"
INVALID_INVITE_CODE = "❌ Invalid or already used invite code. Try another one."

# Registration success messages
REGISTRATION_COMPLETE = """*Wallet connected, but I don't feel the connection...*

Looks like you don't have any $TETRIX in your wallet. To help me survive (and get my gratitude points) buy at least a few $TETRIX on one of these platforms:

- [Geckoterminal](https://www.geckoterminal.com/ton/pools/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)
- [Dexscreener](https://dexscreener.com/ton/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)
- [Blum](https://t.me/blum/app?startapp=memepadjetton_TETRIX_fcNMl-ref_NJU05j3Sv4)"""

# Statistics
STATS_TEMPLATE = """*My vital signs:*

`{emotion[0]}`
`{emotion[1]}`
`{emotion[2]}`

Health
`{health_bar}`
Strength
`{strength_bar}`
Mood
`{mood_bar}`

You've already earned
gratitude points: *{points}*

What you got them for:
For holding: *{holding_points}*
For invites: *{invite_points}*
Old friends bonus: *{early_backer_bonus}*

""" + BOT_SIGNATURE

# Wallet creation guide
WALLET_CREATION_GUIDE = """Let's create a TON wallet:

1. Open @wallet in Telegram
2. Enable TON Space Beta in settings
3. Create TON Space, saving the secret phrase
4. Return here to connect

💡 Any other non-custodial TON wallet will also work"""

# Buttons
BUTTONS = {
    "connect_wallet": "Connect wallet",
    "create_wallet": "Create new...",
    "have_invite": "I have a code",
    "back": "Back",
    "back_to_stats": "Back to stats",
    "open_menu": "Open menu",
    "show_invites": "Show invite codes",
    "refresh_invites": "Refresh list",
    "stats": "Show dashboard",
    "refresh_stats": "Refresh stats"
} 