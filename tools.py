from fpapi import FreedomPop
from peewee import *
import time
import json


db = SqliteDatabase('mydb.db')

class User(Model):
	name = CharField()
	user_id = CharField(unique=True)
	fp_user = CharField(null=True)
	fp_pass = CharField(null=True)

	class Meta:
		database = db

	def __init__(self, *args, **kwargs):
		self.api = None
		super(User, self).__init__(*args, **kwargs)

	def timestamp2Str(self, timestamp):
		return str(timestamp).replace('.', '').ljust(13, '0')

	def initAPI(self):
		if not self.api:
			self.api = FreedomPop(self.fp_user, self.fp_pass)

	def checkNewSMS(self, range):  # TODO change from range to read/unread messages
		self.initAPI()
		currTime = float(time.time())
		pastTime = currTime - range
		req = self.api.getSMS(self.timestamp2Str(pastTime), self.timestamp2Str(currTime), False, False)
		if req.status_code == 200:
			return json.loads(req.content)
		else:
			return False;

def create_tb():
	User.create_table(True)
