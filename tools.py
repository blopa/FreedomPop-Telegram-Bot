from fpapi import FreedomPop
from peewee import *
import time
import sys
import json
from cryptography.fernet import Fernet

CRYPTO = Fernet(sys.argv[2])
db = SqliteDatabase('mydb.db')


class User(Model):
    name = CharField()
    user_id = CharField(unique=True)
    fp_user = CharField(null=True)
    fp_pass = CharField(null=True)
    conver_state = CharField()

    class Meta:
        database = db

    def __init__(self, *args, **kwargs):
        self.api = None
        super(User, self).__init__(*args, **kwargs)

    def timestamp2Str(self, timestamp):
        return str(timestamp).replace('.', '').ljust(13, '0')

    def initAPI(self):
        if not self.api:
            decrypt_pass = decrypt(str(self.fp_pass))
            self.api = FreedomPop(self.fp_user, decrypt_pass)

    def checkNewSMS(self, range):  # TODO change from range to read/unread messages
        self.initAPI()
        currTime = float(time.time())
        pastTime = currTime - range
        return self.api.getSMS(self.timestamp2Str(pastTime), self.timestamp2Str(currTime), False, False)


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
