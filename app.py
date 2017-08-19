#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ForceReply
import bot_user
import logging
import time
import re

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
USERS = []
EMAIL = re.compile("[^@]+@[^@]+\.[^@]+")
END, USER_STEP, PASS_STEP, ACCESS, COMP_STATE, SEND_TEXT, SEND_NUMBER = range(7)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    result = bot_user.User.select().where(bot_user.User.user_id == usr.id).execute()
    if result:
        userdb = bot_user.User.get(bot_user.User.user_id == usr.id)
        update.message.reply_text("Hello there. What do you want to do?")
    else:
        update.message.reply_text("Hello, I'm a bot that allow you to log into your FreedomPop account and start receiving and sending SMS from Telegram! AWESOME, right?")
        userdb = bot_user.User(name=usr.first_name, user_id=usr.id, conversation_state=PASS_STEP, created_at=time.time(), updated_at=time.time())
        if userdb.save():
            update.message.reply_text("Please send me your FreedomPop e-mail.")


def getUsers():
    global USERS
try:
    USERS = list(bot_user.User.select())
except Exception as e:
    logger.exception(e)


def help(bot, update):
    update.message.reply_text('Help!')


def text(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    result = bot_user.User.select().where(bot_user.User.user_id == usr.id).execute()
    if result:
        userdb = bot_user.User.get(bot_user.User.user_id == usr.id)
        if userdb.fp_user == None:
            if not EMAIL.match(msg):
                update.message.reply_text("that dosent look like a valid email")
            else:
                result = bot_user.User.update(fp_user=update.message.text, conversation_state=ACCESS).where(bot_user.User.user_id == usr.id)
                if result.execute():
                    update.message.reply_text('Great! Now send me the password.')

    if update.message.reply_to_message != None:
        return
    update.message.reply_text(update.message.text)
    bot.send_message(update.message.from_user.id, 'text', reply_markup=ForceReply(True, False))


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def new_message(bot, update, args):
    if args.__len__() > 1:
        update.message.reply_text("that dosent look like a phone number")
    update.message.reply_text(update.message.text)


def cancel(bot, update):
    return


def remove_account(bot, update):
    return


def confirm_remove(bot, update):
    return


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
    dp.add_handler(CommandHandler("new", new_message, pass_args=True))
    dp.add_handler(MessageHandler(Filters.command, other_commands))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, text))

    # log all errors
    dp.add_error_handler(error)

    # load users
    bot_user.db.connect()
    bot_user.create_tb()
    getUsers()
    # start sms thread

    # Start the Bot polling
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()