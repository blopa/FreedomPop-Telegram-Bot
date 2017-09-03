#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Bot
import User
import Contact
import logging
import time
import re
import random
import cgi
import string
from threading import Thread
from datetime import datetime
from api import FreedomPop
from pprint import pprint
import ConfigParser

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
USERS = []
EMAIL = re.compile("[^@]+@[^@]+\.[^@]+")
END, USER_STEP, PASS_STEP, ACCESS, COMP_STATE, SEND_TEXT, SEND_NUMBER, REMOVE_ACCOUNT = range(8)
ALPHABET = string.ascii_lowercase[::-1]
Config = ConfigParser.ConfigParser()
Config.read("config.ini")
#  app messages
DEFAULT_MESSAGE = "Hello there. What can I do for you? You could try /new_message or /plan_usage"
ABOUT_MESSAGE = "I'm a bot that allow you to log into your FreedomPop account and start receiving and sending SMS from Telegram! AWESOME, right?"
EMAIL_MESSAGE = "Please send me your FreedomPop e-mail."
PASSWORD_MESSAGE = "Great! Now send me the password."
INVALID_EMAIL_MESSAGE = "Hmn.. that dosen't look like a valid email. Could you please try again?"
INVALID_PHONE_MESSAGE = "Hmn.. that dosen't look like a valid phone number. Could you please try again?"
PHONE_TIP_MESSAGE = 'Try typing "/new" plus a valid phone number, like "/new <PHONE_NUMBER>".'
UNABLE_TO_CONNECT = "I was unable to connect to your FreedomPop account :( please send us your email and password again."
WRONG_CREDENTIALS_MESSAGE = "Something is wrong with your credentials, please register again using the /start command."
CONNECTING_MESSAGE = "Connecting..."
CONNECTED_MESSAGE = "Hooray, we are good to go! If you ever want to remove your account, simply send /remove_account."
SEND_NUMBER_MESSAGE = "Alright, send me the phone number w/ country code or /cancel to cancel."
SEND_MESSAGE_MESSAGE = "Alright, send the message or /cancel to cancel."
SENDING_MESSAGE_MESSAGE = "Trying to send the message..."
MESSAGE_SENT_MESSAGE = "Message sent!! YAY"
REMOVE_ACCOUNT_MESSAGE = "Really? :( send /confirm_remove to confirm or /cancel to cancel."
NOT_LOGGED_MESSAGE = "You are not logged."
ACCOUNT_REMOVED_MESSAGE = "Ok, account removed. Please give my maker a feedback about me :D @PabloMontenegro. Send /start to start again."
CANCELED_MESSAGE = "Ok, canceled."
ERROR_MESSAGE = "Sorry I didn't get that!"
UNKNOWN_ERROR_MESSAGE = "Oops! Something went wrong. Please try again later."


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    usr = update.message.from_user
    #  msg = update.message.text
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:
        #  userdb = User.User.get(User.User.user_id == usr.id)
        #  userdb = result.first()
        send_bot_reply(update, DEFAULT_MESSAGE)
    else:
        send_bot_reply(update, "Hello, " + ABOUT_MESSAGE)
        userdb = User.User(name=usr.first_name, user_id=usr.id, conversation_state=PASS_STEP, created_at=time.time(), updated_at=time.time())
        if userdb.save():
            send_bot_reply(update, EMAIL_MESSAGE)


def text(bot, update):  # handle all messages that are not commands
    usr = update.message.from_user
    msg = update.message.text
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        # REGISTRATION BLOCK ---------------------------------------------------------
        if userdb.fp_user is None:  # check if user has a registered email
            if not EMAIL.match(msg):
                send_bot_reply(update, INVALID_EMAIL_MESSAGE)
            else:
                userdb.fp_user = msg
                userdb.conversation_state = ACCESS
                if userdb.save():
                    send_bot_reply(update, PASSWORD_MESSAGE)
        elif userdb.fp_pass is None:  # check if user has a registered password
            encrypt_pass = User.encrypt(msg)
            userdb.fp_pass = encrypt_pass
            send_bot_reply(update, CONNECTING_MESSAGE)
            fpapi = FreedomPop.FreedomPop(userdb.fp_user, User.decrypt(userdb.fp_pass))
            if fpapi.initialize_token():
                userdb.fp_api_token = fpapi.access_token  # get api token
                userdb.fp_api_refresh_token = fpapi.refresh_token  # get api refresh token
                userdb.fp_api_token_expiration = fpapi.token_expire_timestamp  # get api token expiration date
                if userdb.save():
                    send_bot_reply(update, CONNECTED_MESSAGE)
                    global USERS
                    USERS = list(User.User.select())
            else:
                userdb.fp_user = None
                userdb.fp_pass = None
                if userdb.save():
                    send_bot_reply(update, UNABLE_TO_CONNECT)
        # SENDING MESSAGES BLOCK ---------------------------------------------------------
        else:  # has user and password registered
            if update.message.reply_to_message is not None:  # replying to a message
                phone_number = get_phone_number(update.message.reply_to_message.text)
                if phone_number:
                    userdb.conversation_state = SEND_TEXT
                    userdb.send_text_phone = phone_number
                    if userdb.save():
                        send_text_message(update, userdb, msg)
                else:
                    send_bot_reply(update, DEFAULT_MESSAGE)
            elif int(userdb.conversation_state) == SEND_NUMBER:  # just sent the phone number
                phone_number = validate_phone_number(msg)
                if phone_number:
                    userdb.conversation_state = SEND_TEXT
                    userdb.send_text_phone = phone_number
                    if userdb.save():
                        send_bot_reply(update, SEND_MESSAGE_MESSAGE)
                else:
                    send_bot_reply(update, INVALID_PHONE_MESSAGE)
                    send_bot_reply(update, PHONE_TIP_MESSAGE)
            elif userdb.send_text_phone is not None and int(userdb.conversation_state) == SEND_TEXT:  # just send the text body
                send_text_message(update, userdb, msg)
            else:
                send_bot_reply(update, DEFAULT_MESSAGE)


def get_phone_number(text):
    original_message = text.split('\n', 1)[0]
    if "Reply: /Reply" in original_message:
        phone_number = ""
        reply_hash = original_message[13:].lower()  # remove 'Reply: /Reply'
        for letter in reply_hash:
            phone_number += str(ALPHABET.index(letter))
        return validate_phone_number(phone_number)

    return False


def send_text_message(update, userdb, message):
    fpapi = initialize_freedompop(userdb)
    send_bot_reply(update, SENDING_MESSAGE_MESSAGE)
    if fpapi.send_text_message(userdb.send_text_phone, message):
        send_bot_reply(update, MESSAGE_SENT_MESSAGE)
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
    if args.__len__() > 1:  # sent command + more than one argument
        send_bot_reply(update, INVALID_PHONE_MESSAGE)
        send_bot_reply(update, PHONE_TIP_MESSAGE)
        return
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        if args == []:  # if no argument
            userdb.conversation_state = SEND_NUMBER
            if userdb.save():
                send_bot_reply(update, SEND_NUMBER_MESSAGE)
        else:  # if it has an argument, it should be the phone number
            phone_number = validate_phone_number(args[0])
            if phone_number:
                userdb.send_text_phone = phone_number
                userdb.conversation_state = SEND_TEXT
                if userdb.save():
                    send_bot_reply(update, SEND_MESSAGE_MESSAGE)
            else:
                send_bot_reply(update, INVALID_PHONE_MESSAGE)
                send_bot_reply(update, PHONE_TIP_MESSAGE)


def help(bot, update):
    send_bot_reply(update, 'Help!')


def about(bot, update):
    send_bot_reply(update, ABOUT_MESSAGE)


def cancel(bot, update):
    usr = update.message.from_user
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        if userdb.fp_user is not None and userdb.fp_pass is not None:
            userdb.conversation_state = ACCESS
        userdb.send_text_phone = None
        userdb.save()
    send_bot_reply(update, CANCELED_MESSAGE)


def remove_account(bot, update):
    usr = update.message.from_user
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        userdb.conversation_state = REMOVE_ACCOUNT
        if userdb.save():
            send_bot_reply(update, REMOVE_ACCOUNT_MESSAGE)
    else:
        send_bot_reply(update, NOT_LOGGED_MESSAGE)


def confirm_remove(bot, update):
    usr = update.message.from_user
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        if userdb.conversation_state == REMOVE_ACCOUNT:
            if User.remove_user(userdb.user_id):
                send_bot_reply(update, ACCOUNT_REMOVED_MESSAGE)
            else:
                send_bot_reply(update, UNKNOWN_ERROR_MESSAGE)
    else:
        send_bot_reply(update, NOT_LOGGED_MESSAGE)


def plan_usage(bot, update):
    usr = update.message.from_user
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:  # check if user is on our database
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
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
            send_bot_reply(update, text)
    else:
        send_bot_reply(update, NOT_LOGGED_MESSAGE)


def other_commands(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    result = User.User.select().where(User.User.user_id == usr.id)
    if result:
        #  userdb = User.User.get(User.User.user_id == usr.id)
        userdb = result.first()
        phone_number = get_phone_number("Reply: " + msg)
        if phone_number:
            userdb.conversation_state = SEND_TEXT
            userdb.send_text_phone = phone_number
            if userdb.save():
                send_bot_reply(update, SEND_MESSAGE_MESSAGE)
        else:
            send_bot_reply(update, ERROR_MESSAGE)
    else:
        send_bot_reply(update, ERROR_MESSAGE)


def send_bot_reply(update, message):
    try:
        update.message.reply_text(message)
    except Exception as e:
        logger.exception(e)


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(Config.get('TelegramAPI', 'api_token'))

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("about", about))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("remove_account", remove_account))
    dp.add_handler(CommandHandler("confirm_remove", confirm_remove))
    dp.add_handler(CommandHandler("new_message", new_message))
    dp.add_handler(CommandHandler("plan_usage", plan_usage))
    dp.add_handler(CommandHandler("new", new_message, pass_args=True))
    dp.add_handler(MessageHandler(Filters.command, other_commands))
    dp.add_handler(MessageHandler(Filters.contact, add_contact))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, text))

    # log all errors
    dp.add_error_handler(error)

    # load dbs
    User.initialize_db()
    Contact.initialize_db()
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


def add_contact(bot, update):
    phone_number = ''.join(x for x in update.message.contact.phone_number if x.isdigit())  # clean phone number
    usr = update.message.from_user
    result = Contact.Contact.select().where((Contact.Contact.user_id == usr.id) & (Contact.Contact.phone_number == phone_number))
    if result:
        contact_db = result.first()
        send_bot_reply(update, "You already have +%s on your contacts list saved as %s." % (contact_db.phone_number, contact_db.name))
    else:
        contact_db = Contact.Contact(user_id=usr.id, name=update.message.contact.first_name, phone_number=phone_number, created_at=time.time(), updated_at=time.time())
        if contact_db.save():
            send_bot_reply(update, "Okay, contact saved.")


def checker(*args, **kwargs):  # this is a thread
    time.sleep(5)
    bot = Bot(Config.get('TelegramAPI', 'api_token'))
    while True:
        users = list(USERS)
        before = time.time()
        # print before
        if users:
            try:
                for userdb in users:
                    if userdb.fp_pass is None:
                        continue
                    fpapi = initialize_freedompop(userdb)
                    #  print "checking user: " + userdb.user_id
                    if int(time.time() + 86400) > time.mktime(userdb.fp_api_token_expiration.timetuple()):  # 24 hours
                        fpapi.refresh_access_token()
                        userdb.fp_api_token = fpapi.access_token  # get api token
                        userdb.fp_api_refresh_token = fpapi.refresh_token  # get api refresh token
                        userdb.fp_api_token_expiration = fpapi.token_expire_timestamp  # get api token exp date
                        userdb.save()
                    data = check_new_text_message(fpapi, 7200)  # 2 hours
                    if data is not False:
                        for txt in data['messages']:
                            #  print "SMS arrived!!!"
                            if fpapi.mark_as_read(txt['id']):
                                sender = txt['from']
                                name = ""
                                result = Contact.Contact.select().where((Contact.Contact.user_id == userdb.user_id) & (Contact.Contact.phone_number == sender))
                                if result:
                                    name = result.first().name

                                text = prepare_text(txt, name)
                                bot.sendMessage(chat_id=userdb.user_id, text=text, parse_mode='HTML')
                    else:
                        errors = int(userdb.fp_api_connection_errors)
                        if errors > 50:
                            if User.remove_user(userdb.user_id):
                                bot.sendMessage(chat_id=userdb.user_id, text=WRONG_CREDENTIALS_MESSAGE)
                        else:
                            userdb.fp_api_connection_errors = errors + 1
            except Exception as e:
                logger.exception(e)

        sleep_time = 15 - int(time.time() - before)
        #  print sleep_time
        if sleep_time < 0:
            sleep_time = 1
        time.sleep(sleep_time)


def prepare_text(txt, name):
    reply = ""
    sender = txt['from']  # phone number
    for n in sender:
        letter = ALPHABET[int(n)]
        reply += random.choice([letter.upper(), letter])
    date = datetime.fromtimestamp(float(txt['date'])/1000).strftime('%m/%d/%Y %H:%M:%S')  # date
    content = cgi.escape(txt['body'])  # text content
    sender = "+" + sender
    if name is not "":
        sender = "%s (%s)" % (name, sender)
    return "<b>Reply:</b> /Reply%s\n<b>From: %s @ %s</b>\n\n%s" % (reply, sender, date, content)
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