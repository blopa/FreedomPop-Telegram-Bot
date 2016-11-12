import time

from telegram import Bot
from telegram import (ReplyKeyboardMarkup)
import sys
import thread
import tools
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler)


USER_STEP, PASS_STEP, ACCESS = range(3)
API_KEY = sys.argv[1]
LOGIN = []
USERS = []


def main():
	updater = Updater(API_KEY)
	dispatcher = updater.dispatcher
	# tools.db.connect() TODO
	tools.create_tb()
	getUsers()
	thread.start_new_thread(checker, ('dunno', 2)) # dunno why I am sending this params
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={
			USER_STEP: [MessageHandler(Filters.text, user)],

			PASS_STEP: [MessageHandler(Filters.text, passw)],

			ACCESS: [MessageHandler(Filters.text, access)]
		},

		fallbacks=[CommandHandler('cancel', cancel)]
	)
	dispatcher.add_handler(conv_handler)
	updater.start_polling()


def start(bot, update):
	reply_keyboard = [['Add account']]
	update.message.reply_text(
		'Hello, Im a bot yay',
		reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

	return USER_STEP


def cancel(bot, update):
	return False


def user(bot, update):
	update.message.reply_text('Awesome! Please send me your FreedomPop e-mail')

	return PASS_STEP


def passw(bot, update):
	LOGIN.append(update.message.text) # add email
	update.message.reply_text('Great! Now send me the password.')

	return ACCESS


def access(bot, update):
	LOGIN.append(update.message.text)  # add password
	user = update.message.from_user
	update.message.reply_text('Connecting...')

	userdb = tools.User(name=user.first_name, user_id=user.id, fp_user=LOGIN[0], fp_pass=LOGIN[1])
	userdb = tools.testConn(userdb.fp_user, userdb.fp_pass)
	if userdb.initToken():
		if userdb.save():
			USERS.append(userdb)
		return True
	else:
		return False


def checker(*args, **kwargs):  # this is a thread
	bot = Bot(API_KEY)
	while True:
		for user in USERS:
			data = user.checkNewSMS(604800)
			if data:
				for text in data['messages']:
					print text['body']
					bot.sendMessage(chat_id=user.user_id, text=text['body'])
		time.sleep(30)


def getUsers():
	global USERS
	USERS = tools.User.select()


if __name__ == '__main__':
	main()
