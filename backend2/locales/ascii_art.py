# Emotions for different states
EMOTIONS = {
    "100-81": [
        "  YEE    _@@@_   HAW!  ",
        "    ()  █ ^ ^ █  ()    ",
        "     \__█ \_/ █__/     "
    ],
    "80-61": [
        "  HEHE   __@__     OK  ",
        "    /   █ ^ ^ █   \    ",
        "     \__█  _) █__/     "
    ],
    "60-41": [
        "  JUST   _____   FINE  ",
        "     _  █ o o █  _     ",
        "     /__█  =  █__\     "
    ],
    "40-21": [
        "  OHH    _____   FUCK  ",
        "      / █ > < █ \      ",
        "     /__█  o  █__\     "
    ],
    "20-0": [
        "  SAD    _____   NUMB  ",
        "        █ = = █        ",
        "      __█ /-\ █__      "
    ]
}

def get_emotion_by_percentage(percentage: float) -> list[str]:
    """Get emotion ASCII art based on percentage value"""
    if percentage > 80:
        return EMOTIONS["100-81"]
    elif percentage > 60:
        return EMOTIONS["80-61"]
    elif percentage > 40:
        return EMOTIONS["60-41"]
    elif percentage > 20:
        return EMOTIONS["40-21"]
    else:
        return EMOTIONS["20-0"]

# ASCII art elements for report formatting
REPORT_HEADER = """╔════════════════════════════════════════╗
║ TETRIX PROFILE ANALYZER v1.337        ║
║ Loading personality data...            ║
╚════════════════════════════════════════╝
   [█████████████████████] 100%"""

REPORT_FOOTER = """╔═══════════════════════════════════════════╗
║  > JOIN_TETRIX_UNIVERSE.exe               ║
║  > INITIALIZATION_COMPLETE                ║
║  > WAITING_FOR_YOUR_RESPONSE...          ║
╚═══════════════════════════════════════════╝"""

def get_block_border(width: int = 50) -> tuple[str, str, str]:
    """Get top, title and bottom borders for a block
    Returns tuple of (top_border, title_border, bottom_border)"""
    return (
        f"┌{'─' * (width-2)}┐",
        f"│{{title:^{width-4}}}│",  # Template for title
        f"└{'─' * (width-2)}┘"
    ) 