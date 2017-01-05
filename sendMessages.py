from telegram import Bot
import time
import bot_user
import sys
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = sys.argv[1]
MESSAGE = sys.argv[7]
users = list(bot_user.User.select())
bot = Bot(API_KEY)
print MESSAGE
if users:
    for usr in users:
        print usr.user_id
        try:
            bot.sendMessage(chat_id=usr.user_id, text=MESSAGE, parse_mode='HTML')
            time.sleep(1)
        except Exception as e:
            logger.exception(e)

#  run 'python sendMessages.py <BOT_API> <CRYPT_KEY> <BOTAN_API> <FP_API_CLIENT> <FP_API_SECRET> <FP_APP_VERSION> <MESSAGE_TO_SEND>'