from dotenv import load_dotenv
import os
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_2ID = int(os.getenv("ADMIN_2ID"))
DB_PATH = os.getenv("DB_PATH")