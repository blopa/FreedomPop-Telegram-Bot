import logging
from peewee import *
from cryptography.fernet import Fernet
from peewee import TimestampField
import ConfigParser

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
Config = ConfigParser.ConfigParser()
Config.read("config.ini")
CRYPTO = Fernet(Config.get('Cryptography', 'crypto_key'))
DATABASE = SqliteDatabase('userdb.db')  # create database to interact with

# create a class for users
class User(Model):
    name = CharField()
    user_id = CharField(unique=True)
    conversation_state = IntegerField()
    fp_user = CharField(null=True)
    fp_pass = CharField(null=True)
    fp_api_token = CharField(null=True)
    fp_api_refresh_token = CharField(null=True)
    fp_api_token_expiration = TimestampField(null=True)
    fp_api_connection_errors = IntegerField(default=0)
    send_text_phone = IntegerField(null=True)
    created_at = TimestampField(null=False)
    updated_at = TimestampField(null=False)

    class Meta:
        database = DATABASE

def initialize_db():
    #db.connect()
    DATABASE.create_tables([User], safe=True)
    #db.close()


def remove_user(user_id):
    query = User.delete().where(User.user_id == user_id)
    if query.execute():
        return True
    else:
        return False


def encrypt(plain_text):
    if isinstance(plain_text, basestring):
        string_text = str(plain_text)
        return CRYPTO.encrypt(bytes(string_text))
    else:
        raise Exception('Only strings are allowed.')


def decrypt(cipher_text):
    return CRYPTO.decrypt(str(cipher_text))