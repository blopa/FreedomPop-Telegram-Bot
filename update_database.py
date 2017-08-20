# before running this script, you'll have to add the new tables to the database

from telegram import Bot
import time
import ConfigParser
import User
import logging
from api import FreedomPop

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
Config = ConfigParser.ConfigParser()
Config.read("config.ini")
BOT = Bot(Config.get('TelegramAPI', 'api_token'))
USERS = list(User.User.select())
if USERS:
    for usr in USERS:
        print usr.user_id
        userdb = User.User.get(User.User.user_id == usr.user_id)
        fpapi = FreedomPop.FreedomPop(userdb.fp_user, User.decrypt(userdb.fp_pass))
        if fpapi.initialize_token():
            userdb.fp_api_token = fpapi.access_token  # get api token
            userdb.fp_api_refresh_token = fpapi.refresh_token  # get api refresh token
            userdb.fp_api_token_expiration = fpapi.token_expire_timestamp  # get api token expiration date
            userdb.fp_api_connection_errors = 0
            userdb.created_at = int(time.time()) - 15552000  # 6 months
            userdb.updated_at = time.time()
            userdb.save()
        else:
            BOT.sendMessage(chat_id=usr.user_id, text="Something is wrong with your credentials, please register again using the /start command.", parse_mode='HTML')
            User.remove_user(userdb.user_id)

#  run 'python update_database.py'