import os

# Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "8555121343:AAF3lKPZUdTV5l-OM-4QB6V7ENI3LzPsjvA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6919640732"))

# Channel Info
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002379498816")
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "https://t.me/+UYT1dE4cXuA5NTVl")

# GPLinks API Configuration
GPLINKS_API = os.getenv("GPLINKS_API", "28f7b134d7e185764342aa508fdb2a43b1e93970")

# Database Path
DB_PATH = "bot_database.db"
