import sys
import logging
from api.freedompop import FreedomPop
from peewee import *
from cryptography.fernet import Fernet
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CRYPTO = Fernet(sys.argv[2])
db = SqliteDatabase('userdb.db')


class User(Model):
    name = CharField()
    user_id = CharField(unique=True)
    fp_user = CharField(null=True)
    fp_pass = CharField(null=True)
    fp_api_token = CharField(null=True)
    fp_api_token_expiration = DateTimeField(null=True)
    created_at = DateTimeField(null=False)
    updated_at = DateTimeField(null=False)
    conversation_state = CharField()

    class Meta:
        database = db

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)


def create_tb():
    User.create_table(True)


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
    return CRYPTO.decrypt(cipher_text)
