import time

from telegram import Bot
from telegram import (ReplyKeyboardMarkup)
import sys
import thread
import tools
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler)


USER_STEP, PASS_STEP, ACCESS, END = range(4)
API_KEY = sys.argv[1]
LOGIN = []
USERS = [] #tools.User
EMAIL = '[^@]+@[^@]+\.[^@]+'


def main():
	updater = Updater(API_KEY)
	dispatcher = updater.dispatcher
	tools.db.connect()
	tools.create_tb()
	getUsers()
	thread.start_new_thread(checker, ('dunno', 2)) # dunno why I am sending this params
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={
			USER_STEP: [RegexHandler('^(Add account)$', user)],

			PASS_STEP: [RegexHandler(EMAIL, passw)],

			ACCESS: [MessageHandler(Filters.text, access)],

			END: [MessageHandler(Filters.text, end)]
		},

		fallbacks=[CommandHandler('cancel', cancel)]
	)
	dispatcher.add_handler(conv_handler)
	updater.start_polling()


def end(bot, update):
	return ConversationHandler.END


def start(bot, update):
	reply_keyboard = [['Add account']]
	update.message.reply_text(
		'Hello, Im a bot yay',
		reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

	return USER_STEP


def cancel(bot, update):
	return False


def user(bot, update):
	user = update.message.from_user
	result = tools.User.select().where(tools.User.user_id == user.id)
	if result:
		update.message.reply_text('Ops, it seems that you already have an account with us!')
		return END
	else:
		update.message.reply_text('Awesome! Please send me your FreedomPop e-mail')
		return PASS_STEP


def passw(bot, update):
	LOGIN.append(update.message.text)  # add email
	update.message.reply_text('Great! Now send me the password.')

	return ACCESS


def access(bot, update):
	global USERS
	LOGIN.append(update.message.text)  # add password
	user = update.message.from_user
	update.message.reply_text('Connecting...')

	userdb = tools.User(name=user.first_name, user_id=user.id, fp_user=LOGIN[0], fp_pass=LOGIN[1])
	#userdb = tools.testConn(userdb.fp_user, userdb.fp_pass)
	if userdb.getConn():
		if userdb.save():
			#USERS.append(userdb) TODO
			USERS = tools.User.select()
			update.message.reply_text('Hooray, we are good to go!')
		else:
			update.message.reply_text('Something went wrong, send us your password again!')
		return PASS_STEP
	else:
		update.message.reply_text('Ops, your username of password doesent seem right, please try again')
		return USER_STEP


def checker(*args, **kwargs):  # this is a thread
	bot = Bot(API_KEY)
	while True:
		print 'to rodando'
		before = time.time()
		users = list(USERS)
		if users:
			for user in users:
				data = user.checkNewSMS(86400)  # 604800
				if data:
					for text in data['messages']:
						print text['body']
						bot.sendMessage(chat_id=user.user_id, text=text['body'])
		duration = time.time() - before
		#time.sleep(30 - (duration * 1000))
		time.sleep(5)


def getUsers():
	global USERS
	USERS = tools.User.select()


if __name__ == '__main__':
	main()
