import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

DAILY_DEFEND_LIMIT = 3
EARLY_BONUS_LIMIT = 5
CHECKIN_REWARD = 5

try:
    MCN_OWNER_ID = int(os.getenv("MCN_OWNER_ID", ""))
except ValueError:
    MCN_OWNER_ID = None