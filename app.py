import time
import datetime
from telegram import Bot
from telegram import (ReplyKeyboardMarkup)
import sys
import thread
import tools
import string
import random
import re
import cgi
import botan
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


END, USER_STEP, PASS_STEP, ACCESS, COMP_STATE, SEND_TEXT, SEND_NUMBER = range(7)
API_KEY = sys.argv[1]
LOGIN = []
USERS = []  #tools.User
EMAIL = re.compile("[^@]+@[^@]+\.[^@]+")
ALPHABET = string.ascii_lowercase[::-1]
REPLY_TO = {}
ERROR_CONN = {}
FLAG_DEL = {}
botan_token = sys.argv[5]


def main():
    updater = Updater(API_KEY)
    dispatcher = updater.dispatcher
    tools.db.connect()
    tools.create_tb()
    getUsers()
    # tools.db.close()
    thread.start_new_thread(checker, ('dunno', 2))  # dunno why I am sending this params
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.all, start)],

        states={
            USER_STEP: [MessageHandler(Filters.text, user)],

            PASS_STEP: [MessageHandler(Filters.text, passw)],

            ACCESS: [MessageHandler(Filters.text, access)],

            COMP_STATE: [MessageHandler(Filters.command, composeState)],

            SEND_TEXT: [MessageHandler(Filters.all, sendText)],

            SEND_NUMBER: [MessageHandler(Filters.all, sendNumber)],

            END: [MessageHandler(Filters.text, end)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv_handler)
    updater.start_polling()


def end(bot, update):
    return ConversationHandler.END


def start(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if msg:
        result = tools.User.select().where(tools.User.user_id == usr.id).execute()
        if result:
            userdb = tools.User.get(tools.User.user_id == usr.id)
            funcs = {1: user, 2: passw, 3: access, 4: composeState, 5: sendText}
            return funcs[int(userdb.conver_state)](bot, update)
        else: #  elif msg.startswith('/start'):
            reply_keyboard = [['Register account']]
            update.message.reply_text('Hello, Im a bot that allow you to log into your FreedomPop account and start '
                                      'receiving and sending SMS from Telegram! AWESOME, right?',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return USER_STEP

    return END


def cancel(bot, update):
    return False


def user(bot, update):
    usr = update.message.from_user
    if update.message.text != "Register account":
        update.message.reply_text('Sorry, I didnt understand that, try again. Try typing "Register account".')
        return END

    result = tools.User.select().where(tools.User.user_id == usr.id)
    if result.execute():
        update.message.reply_text('Ops, it seems that you already have an account with us!')
        return END

    userdb = tools.User(name=usr.first_name, user_id=usr.id, conver_state=PASS_STEP)
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

    result = tools.User.update(fp_user=update.message.text, conver_state=ACCESS).where(tools.User.user_id == usr.id)
    if result.execute():
        update.message.reply_text('Great! Now send me the password.')
        return ACCESS
    else:
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
    userdb.initAPI()
    if userdb.api.initToken():
        try:
            if userdb.save():
                result = tools.User.update(conver_state=COMP_STATE).where(tools.User.user_id == usr.id)
                if result.execute():
                    USERS = list(tools.User.select())
                    update.message.reply_text('Hooray, we are good to go!')
                    update.message.reply_text('User /new_message to compose a new message. Or simply /new <PHONE_NUMBER>')
                    try:
                        botan.track(botan_token, update.message.from_user.id, {0: 'user registered'}, 'user registered')
                    except Exception as e:
                        logger.exception(e)
                    return COMP_STATE
                else:
                    update.message.reply_text('Something went wrong, send us your password again!')
                    return PASS_STEP
            else:
                update.message.reply_text('Something went wrong, send us your password again!')
                return PASS_STEP
        except Exception as e:
            logger.exception(e)
    else:
        update.message.reply_text('Ops, your username or password doesnt seem right, please try again')
        return USER_STEP


def checkConnProblem(update, user_id):
    if user_id in FLAG_DEL:
        if FLAG_DEL[user_id] == '1':
            if tools.remove_user(user_id):
                update.message.reply_text('Something is wrong with your credentials, please register again')
                del FLAG_DEL[user_id]
                return True
    return False


def sendNumber(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if checkConnProblem(update, usr.id):
        return END
    if msg:
        if msg != "/cancel":
            non_decimal = re.compile(r'[^\d]+')
            msg = non_decimal.sub('', msg)
            if msg:
                REPLY_TO[usr.id] = msg
                update.message.reply_text('Alright, send the message or /cancel to cancel.')
                return SEND_TEXT
            else:
                update.message.reply_text('Sorry, that dosent look like a valid phone number.')
        else:
            update.message.reply_text('Ok, canceled.')

    return COMP_STATE


def sendText(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if checkConnProblem(update, usr.id):
        return END
    if msg:
        if msg != "/cancel":
            replyto = REPLY_TO[usr.id]
            userdb = tools.User.get(tools.User.user_id == usr.id)
            userdb.initAPI()
            userdb.api.initToken()
            if userdb.api.sendSMS(replyto, msg):
                del REPLY_TO[usr.id]
                try:
                    botan.track(botan_token, update.message.from_user.id, {0: 'message sent'}, 'message sent')
                except Exception as e:
                    logger.exception(e)
                update.message.reply_text('Message sent! YAY')
                smsbalance = userdb.api.getSMSBalance()
                if int(smsbalance['balanceSMS']) < 20:
                    rep_text = 'You have only ' + smsbalance['balanceSMS'] + ' SMS left out of ' + smsbalance['baseSMS'] + ' from your "' + smsbalance['planName'] + '" plan.'
                    update.message.reply_text(rep_text)
            else:
                update.message.reply_text('Something went wrong, try again!')
        else:
            update.message.reply_text('Ok, message canceled.')

    return COMP_STATE


def composeState(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    if checkConnProblem(update, usr.id):
        return END
    if msg.startswith("/Reply"):
        msg = msg[6:].lower()
        replyto = ""
        for l in msg:
            replyto += str(ALPHABET.index(l))
        REPLY_TO[usr.id] = replyto
        update.message.reply_text('Alright, send the message or /cancel to cancel.')
        return SEND_TEXT
    elif msg.startswith("/new_message"):
        update.message.reply_text('Alright, send me the phone number w/ country code or /cancel to cancel.')
        return SEND_NUMBER
    elif msg.startswith("/new"): #  TODO DRY
        non_decimal = re.compile(r'[^\d]+')
        msg = non_decimal.sub('', msg[4:])
        if msg:
            REPLY_TO[usr.id] = msg
            update.message.reply_text('Alright, send the message or /cancel to cancel.')
            return SEND_TEXT
        else:
            update.message.reply_text('Sorry, that doesnt look like a valid phone number.')
    else:
        update.message.reply_text('Sorry, I didnt understand that, try again.')

    return COMP_STATE


def prepareText(txt):
    reply = ""
    sender = txt['from']  # phone number
    for n in sender:
        letter = ALPHABET[int(n)]
        reply += random.choice([letter.upper(), letter])
    #  reply = reply.encode('rot13')  # obfuscated phone number
    date = datetime.datetime.fromtimestamp(float(txt['date'])/1000).strftime('%d/%m/%Y %H:%M:%S')  # date
    content = cgi.escape(txt['body'])  # text content
    return "<b>Reply:</b> /Reply%s\n<b>From: +%s @ %s</b>\n\n%s" % (reply, sender, date, content)


def checker(*args, **kwargs):  # this is a thread
    time.sleep(5)
    bot = Bot(API_KEY)
    while True:
        before = time.time()
        users = list(USERS)
        if users:
            for usr in users:
                data = usr.checkNewSMS(7200)  # 604800 86400
                if data:
                    if usr.user_id in ERROR_CONN:
                        del ERROR_CONN[usr.user_id]
                    for txt in data['messages']:
                        if usr.api.setAsRead(txt['id']):
                            text = prepareText(txt)
                            bot.sendMessage(chat_id=usr.user_id, text=text, parse_mode='HTML')
                            try:
                                botan.track(botan_token, usr.user_id, {0: 'message received'}, 'message received')
                            except Exception as e:
                                logger.exception(e)
                else:
                    if usr.user_id not in ERROR_CONN:
                        ERROR_CONN[usr.user_id] = str(time.time())
                    elif time.time() > float(ERROR_CONN[usr.user_id]) + 86400:
                        FLAG_DEL[usr.user_id] = '1'

        sleeptime = 15 - int(time.time() - before)
        time.sleep(sleeptime)
        #time.sleep(5)


def getUsers():
    global USERS
    try:
        USERS = list(tools.User.select())
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    main()
