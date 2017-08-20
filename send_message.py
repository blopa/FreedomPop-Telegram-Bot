from telegram import Bot
import time
import ConfigParser
import User
import sys
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
Config = ConfigParser.ConfigParser()
Config.read("config.ini")
MESSAGE = sys.argv[1]
USERS = list(User.User.select())
BOT = Bot(Config.get('TelegramAPI', 'api_token'))
print MESSAGE
if USERS:
    for usr in USERS:
        print usr.user_id
        try:
            BOT.sendMessage(chat_id=usr.user_id, text=MESSAGE, parse_mode='HTML')
            time.sleep(1)
        except Exception as e:
            logger.exception(e)

#  run 'python send_message.py MESSAGE_TO_SEND'