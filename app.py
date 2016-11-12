from telegram import (ReplyKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler)
import sys
import json
import logging
from fpapi import FreedomPop
import time

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

USER, PASS, TESTCONN, OK, NOTOK = range(5)
API_KEY = sys.argv[1]
LOGIN = []


def timestamp2Str(timestamp):
	return str(timestamp).replace('.', '').ljust(13, '0')


def checkNewSMS(freedompop):
	currTime = float(time.time())
	pastTime = currTime - 604800  # one minute
	req = freedompop.getSMS(timestamp2Str(pastTime), timestamp2Str(currTime), False, True)
	if req.status_code == 200:
		return json.loads(req.content)
	else:
		return False;


def start(bot, update):
	reply_keyboard = [['Add account']]

	update.message.reply_text(
		'Hello, Im a bot yay',
		reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

	return USER


def user(bot, update):
	update.message.reply_text('Awesome! Please send me your FreedomPop e-mail')

	return PASS


def passw(bot, update):
	LOGIN.append(update.message.text)
	update.message.reply_text('Great! Now send me the password.')
	print LOGIN

	return TESTCONN


def testconn(bot, update):
	LOGIN.append(update.message.text)
	fp = FreedomPop(LOGIN[0], LOGIN[1])
	sms = checkNewSMS(fp)
	ret = ""

	if not sms:
		update.message.reply_text('nops :(')
		return NOTOK

	for text in sms['messages']:
		print text['body']
		ret += str(text['body']) + " | "

	update.message.reply_text(ret)

	return OK



def notok(bot, update):
	return ConversationHandler.END


def ok(bot, update):
	user = update.message.from_user
	logger.info("Bio of %s: %s" % (user.first_name, update.message.text))
	update.message.reply_text('Thank you! I hope we can talk again some day.')

	return ConversationHandler.END


def cancel(bot, update):
	user = update.message.from_user
	logger.info("User %s canceled the conversation." % user.first_name)
	update.message.reply_text('Bye! I hope we can talk again some day.')

	return ConversationHandler.END


def error(bot, update, error):
	logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
	# Create the EventHandler and pass it your bot's token.
	updater = Updater(API_KEY)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	# Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={
			USER: [RegexHandler('^(Add account)$', user)],

			PASS: [MessageHandler(Filters.text, passw)],

			TESTCONN: [MessageHandler(Filters.text, testconn)],

			OK: [MessageHandler(Filters.text, ok)],

			NOTOK: [MessageHandler(Filters.text, notok)]
		},

		fallbacks=[CommandHandler('cancel', cancel)]
	)

	dp.add_handler(conv_handler)

	# log all errors
	dp.add_error_handler(error)

	# Start the Bot
	updater.start_polling()

	# Run the bot until the you presses Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	main()
