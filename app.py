#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Bot
from telegram import ForceReply
import User
import logging
import time
import re
import random
import cgi
import string
from threading import Thread
from datetime import datetime
from api import FreedomPop

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
USERS = []
EMAIL = re.compile("[^@]+@[^@]+\.[^@]+")
END, USER_STEP, PASS_STEP, ACCESS, COMP_STATE, SEND_TEXT, SEND_NUMBER = range(7)
ALPHABET = string.ascii_lowercase[::-1]


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    result = User.User.select().where(User.User.user_id == usr.id).execute()
    if result:
        userdb = User.User.get(User.User.user_id == usr.id)
        update.message.reply_text("Hello there. What do you want to do?")
    else:
        update.message.reply_text("Hello, I'm a bot that allow you to log into your FreedomPop account and start receiving and sending SMS from Telegram! AWESOME, right?")
        userdb = User.User(name=usr.first_name, user_id=usr.id, conversation_state=PASS_STEP, created_at=time.time(), updated_at=time.time())
        if userdb.save():
            update.message.reply_text("Please send me your FreedomPop e-mail.")


def help(bot, update):
    update.message.reply_text('Help!')


def text(bot, update):  # handle all messages that are not commands
    usr = update.message.from_user
    msg = update.message.text
    result = User.User.select().where(User.User.user_id == usr.id).execute()
    if result:  # check if user is on our database
        userdb = User.User.get(User.User.user_id == usr.id)
        if userdb.fp_user is None:  # check if user has a registred email
            if not EMAIL.match(msg):
                update.message.reply_text("that dosent look like a valid email")
            else:
                userdb.fp_user = msg
                userdb.conversation_state = ACCESS
                if userdb.save():
                    update.message.reply_text('Great! Now send me the password.')
        elif userdb.fp_pass is None:  # check if user has a registred password
            encrypt_pass = User.encrypt(msg)
            userdb.fp_pass = encrypt_pass
            update.message.reply_text('Connecting...')
            fpapi = FreedomPop.FreedomPop(userdb.fp_user, User.decrypt(userdb.fp_pass))
            if fpapi.initialize_token():
                userdb.fp_api_token = fpapi.access_token  # get api token
                userdb.fp_api_refresh_token = fpapi.refresh_token  # get api refresh token
                userdb.fp_api_token_expiration = fpapi.token_expire_timestamp  # get api token expiration date
                if userdb.save():
                    update.message.reply_text("Hooray, we are good to go! If you ever want to remove your account, simply send /remove_account.")
                    global USERS
                    USERS = list(User.User.select())
            else:
                userdb.fp_user = None
                userdb.fp_pass = None
                if userdb.save():
                    update.message.reply_text("I was unable to connect to your freedompop account, please send us your email and password again")
        else:  # has user and password registered
            if update.message.reply_to_message is not None:  # replying to a message
                original_message = update.message.reply_to_message.text.split('\n', 1)[0]
                if "Reply: /Reply" in original_message:
                    phone_number = ""
                    reply_hash = original_message[13:].lower()  # remove 'Reply: /Reply'
                    for letter in reply_hash:
                        phone_number += str(ALPHABET.index(letter))
                    phone_number = validate_phone_number(phone_number)
                    if phone_number:
                        userdb.conversation_state = SEND_TEXT
                        userdb.send_text_phone = phone_number
                        if userdb.save():
                            send_text_message(update, userdb, msg)
                else:
                    update.message.reply_text("hello, what can I help you with?")
            elif userdb.conversation_state == SEND_NUMBER:  # just sent the phone number
                phone_number = validate_phone_number(msg)
                if phone_number:
                    userdb.conversation_state = SEND_TEXT
                    userdb.send_text_phone = phone_number
                    if userdb.save():
                        update.message.reply_text("ok now send the message")
                else:
                    update.message.reply_text("that dosen't look like a valid phone number")

            if userdb.send_text_phone is not None and userdb.conversation_state == SEND_TEXT:  # just send the text body
                send_text_message(update, userdb, msg)


def send_text_message(update, userdb, message):
    fpapi = initialize_freedompop(userdb)
    update.message.reply_text("trying to send the message...")
    if fpapi.send_text_message(userdb.send_text_phone, message):
        update.message.reply_text("YAY message sent")
        userdb.send_text_phone = None
        userdb.conversation_state = COMP_STATE
        userdb.save()


def validate_phone_number(message):
    non_decimal = re.compile(r'[^\d]+')
    number = non_decimal.sub('', message)
    if number == "":
        return False
    return number


def initialize_freedompop(userdb):
    fpapi = FreedomPop.FreedomPop(userdb.fp_user, User.decrypt(userdb.fp_pass))
    fpapi.access_token = userdb.fp_api_token
    fpapi.refresh_token = userdb.fp_api_refresh_token
    fpapi.token_expire_timestamp = userdb.fp_api_token_expiration

    return fpapi


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def new_message(bot, update, args):
    usr = update.message.from_user
    msg = update.message.text
    if args.__len__() > 1:  # sent command + more than one argument
        update.message.reply_text("that dosent look like a phone number")
        return
    result = User.User.select().where(User.User.user_id == usr.id).execute()
    if result:  # check if user is on our database
        userdb = User.User.get(User.User.user_id == usr.id)
        if args == []:  # if no argument
            userdb.conversation_state = SEND_NUMBER
            if userdb.save():
                update.message.reply_text("ok send me the phone numher")
        else:  # if it has an argument, it should be the phone number
            phone_number = validate_phone_number(args[0])
            if phone_number:
                userdb.send_text_phone = phone_number
                userdb.conversation_state = SEND_TEXT
                if userdb.save():
                    update.message.reply_text("ok now send the message")
            else:
                update.message.reply_text("that dosent look like a phone number")


def cancel(bot, update):
    return


def remove_account(bot, update):
    return


def confirm_remove(bot, update):
    return


def plan_usage(bot, update):
    usr = update.message.from_user
    result = User.User.select().where(User.User.user_id == usr.id).execute()
    if result:  # check if user is on our database
        userdb = User.User.get(User.User.user_id == usr.id)
        if userdb.fp_user is not None and userdb.fp_pass is not None:
            text = "Please check your plan details below:\n\n"
            fpapi = initialize_freedompop(userdb)
            balance = fpapi.get_plan_balance()
            if not balance:
                balance = fpapi.get_usage()
            if not balance:
                balance = fpapi.get_text_messages_balance()
            for dt in balance:
                in_mb = 1024 * 1024
                label = dt[0].upper() + dt[1:]
                content = balance[dt]
                if dt == "remainingData" or dt == "dataFriendBonusEarned" or dt == "baseData":
                    content = str(int(balance[dt]) / in_mb) + " MB"
                text += label + ": " + content + "\n"
            update.message.reply_text(text)
    else:
        update.message.reply_text("You are not logged.")


def other_commands(bot, update):
    return


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("257322944:AAEBk4rQKxskBrmNqvwScsmDmIfvxj2wcAs")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("remove_account", remove_account))
    dp.add_handler(CommandHandler("confirm_remove", confirm_remove))
    dp.add_handler(CommandHandler("new_message", new_message))
    dp.add_handler(CommandHandler("plan_usage", plan_usage))
    dp.add_handler(CommandHandler("new", new_message, pass_args=True))
    dp.add_handler(MessageHandler(Filters.command, other_commands))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, text))

    # log all errors
    dp.add_error_handler(error)

    # load users
    User.initialize_db()
    global USERS
    USERS = list(User.User.select())
    # start sms thread

    # Start the Bot polling
    updater.start_polling()
    Thread(target=checker).start()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def checker(*args, **kwargs):  # this is a thread
    time.sleep(5)
    bot = Bot("257322944:AAEBk4rQKxskBrmNqvwScsmDmIfvxj2wcAs")
    while True:
        users = list(USERS)
        before = time.time()
        if users:
            for userdb in users:
                if userdb.fp_pass is None:
                    continue
                fpapi = initialize_freedompop(userdb)
                if int(time.time() + 86400) > time.mktime(userdb.fp_api_token_expiration.timetuple()):  # 24 hours
                    fpapi.refresh_access_token()
                    userdb.fp_api_token = fpapi.access_token  # get api token
                    userdb.fp_api_refresh_token = fpapi.refresh_token  # get api refresh token
                    userdb.fp_api_token_expiration = fpapi.token_expire_timestamp  # get api token exp date
                    userdb.save()
                data = check_new_text_message(fpapi, 7200)  # 2 hours
                if data is not False:
                    for txt in data['messages']:
                        if fpapi.mark_as_read(txt['id']):
                            text = prepare_text(txt)
                            bot.sendMessage(chat_id=userdb.user_id, text=text, parse_mode='HTML')
        sleep_time = 15 - int(time.time() - before)
        if sleep_time < 0:
            sleep_time = 1
        time.sleep(sleep_time)


def prepare_text(txt):
    reply = ""
    sender = txt['from']  # phone number
    for n in sender:
        letter = ALPHABET[int(n)]
        reply += random.choice([letter.upper(), letter])
    #  reply = reply.encode('rot13')  # obfuscated phone number
    date = datetime.fromtimestamp(float(txt['date'])/1000).strftime('%m/%d/%Y %H:%M:%S')  # date
    content = cgi.escape(txt['body'])  # text content
    return "<b>Reply:</b> /Reply%s\n<b>From: +%s @ %s</b>\n\n%s" % (reply, sender, date, content)
    #  return "<b>Reply:</b> /Reply%s\n<b>From:</b> <b><a href='tel:+%s'>+%s</a></b> <b>@ %s</b>\n\n%s" % (reply, sender, sender, date, content) # TODO


def check_new_text_message(fpapi, range):
    try:
        currTime = float(time.time())
        pastTime = currTime - range
        return fpapi.get_text_messages(timestamp_to_string(pastTime), timestamp_to_string(currTime), False, False, False)
    except Exception as e:
        logger.exception(e)
        return False


def timestamp_to_string(timestamp):
    return str(timestamp).replace('.', '').ljust(13, '0')


if __name__ == '__main__':
    main()