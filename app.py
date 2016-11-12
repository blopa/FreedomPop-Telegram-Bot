import time
import datetime
import logging
from telegram import Bot
from telegram import (ReplyKeyboardMarkup)
import sys
import thread
import tools
import string
import random
import re
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


USER_STEP, PASS_STEP, ACCESS, END, REPLY, REPLY_TEXT = range(6)
API_KEY = sys.argv[1]
LOGIN = []
USERS = []  #tools.User
EMAIL = re.compile('[^@]+@[^@]+\.[^@]+')
ALPHABET = string.ascii_lowercase[::-1]
REPLY_TO = {}


def main():
    updater = Updater(API_KEY)
    dispatcher = updater.dispatcher
    tools.db.connect()
    tools.create_tb()
    getUsers()
    tools.db.close()
    thread.start_new_thread(checker, ('dunno', 2))  # dunno why I am sending this params
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            USER_STEP: [MessageHandler(Filters.text, user)],

            PASS_STEP: [MessageHandler(Filters.text, passw)],

            ACCESS: [MessageHandler(Filters.text, access)],

            REPLY: [MessageHandler(Filters.text, reply)],

            REPLY_TEXT: [MessageHandler(Filters.text, replyText)],

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
    usr = update.message.from_user
    if update.message.text != "Add account":
        update.message.reply_text('Sorry, I didnt understand that, try again.')
        return END

    result = tools.User.select().where(tools.User.user_id == usr.id)
    if result:
        update.message.reply_text('Ops, it seems that you already have an account with us!')
        return END

    userdb = tools.User(name=usr.first_name, user_id=usr.id)
    if userdb.save():
        update.message.reply_text('Awesome! Please send me your FreedomPop e-mail')
        return PASS_STEP
    else:
        update.message.reply_text('Ops, something went wrong, try again!')
        return END


def passw(bot, update):
    usr = update.message.from_user
    if not EMAIL.match(update.message.text):
        update.message.reply_text('That dosent seem like a valid email, try again!')
        return PASS_STEP

    result = tools.User.update(fp_user=update.message.text).where(tools.User.user_id == usr.id)
    if result.execute():
        update.message.reply_text('Great! Now send me the password.')
        return ACCESS
    else:
        #  TODO drop user?
        update.message.reply_text('Ops, something went wrong, try again!')
        return END


def access(bot, update):
    global USERS
    usr = update.message.from_user
    encrypt_pass = tools.encrypt(update.message.text)
    result = tools.User.update(fp_pass=encrypt_pass).where(tools.User.user_id == usr.id)
    if not result.execute():
        update.message.reply_text('Ops, something went wrong, try again!')
        return END

    update.message.reply_text('Connecting...')
    userdb = tools.User.get(tools.User.user_id == usr.id)
    # logger.info(userdb)
    userdb.initAPI()
    # logger.info(userdb.api.initToken())
    if userdb.api.initToken():
        try:
            if userdb.save():
                USERS = list(tools.User.select())
                update.message.reply_text('Hooray, we are good to go!')
                return REPLY
            else:
                update.message.reply_text('Something went wrong, send us your password again!')
                return PASS_STEP
        except Exception as e:
            logger.exception(e)
    else:
        update.message.reply_text('Ops, your username or password doesnt seem right, please try again')
        return USER_STEP


def replyText(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if msg != "/cancel":
        replyto = REPLY_TO[usr.id]
        apiuser = tools.User.select().where(tools.User.user_id == usr.id)
        if apiuser.api.sendSMS(replyto, msg):
            del REPLY_TO[usr.id]
            update.message.reply_text('Message sent! YAY')
        else:
            update.message.reply_text('Something went wrong, try again!')
    else:
        update.message.reply_text('Ok, reply canceled.')

    return REPLY


def reply(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if msg.startswith("/Reply"):
        msg = msg[6:].lower()
        replyto = ""
        for l in msg:
            replyto += ALPHABET.index(l)
        REPLY_TO[usr.id] = replyto
        update.message.reply_text('Alright, send the message or /cancel to cancel.')
        return REPLY_TEXT
    else:
        update.message.reply_text('Sorry, I didnt understand that, try again.')

    return REPLY


def prepareText(txt):
    reply = ""
    sender = txt['from']  # phone number
    for n in sender:
        letter = ALPHABET[int(n)]
        reply += random.choice([letter.upper(), letter])
    #  reply = reply.encode('rot13')  # obfuscated phone number
    date = datetime.datetime.fromtimestamp(float(txt['date'])/1000).strftime('%d/%m/%Y %H:%M:%S')  # date
    content = txt['body']  # text content
    return "*Reply:* /Reply%s\n*From: +%s @ %s*\n\n%s" % (reply, sender, date, content)


def checker(*args, **kwargs):  # this is a thread
    bot = Bot(API_KEY)
    while True:
        before = time.time()
        users = list(USERS)
        if users:
            for usr in users:
                data = usr.checkNewSMS(7200)  # 604800 86400
                if data:
                    for txt in data['messages']:
                        #  logger.info(text['body'])
                        if True:  #user.api.setAsRead(txt['id']):
                            text = prepareText(txt)
                            bot.sendMessage(chat_id=usr.user_id, text=text, parse_mode='MARKDOWN')
        duration = time.time() - before
        #  time.sleep(15 - (duration * 1000))
        time.sleep(5)


def getUsers():
    global USERS
    USERS = list(tools.User.select())


if __name__ == '__main__':
    main()
