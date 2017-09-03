import logging
from peewee import *
from peewee import TimestampField
from User import User

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
DATABASE = SqliteDatabase('userdb.db')  # create database to interact with


# create a class for users
class Contact(Model):
    #  id = PrimaryKeyField()
    user_id = CharField(unique=True)
    #  user = ForeignKeyField(User, related_name='contacts')
    name = CharField()
    phone_number = CharField()
    created_at = TimestampField(null=False)
    updated_at = TimestampField(null=False)

    class Meta:
        database = DATABASE

def initialize_db():
    #db.connect()
    DATABASE.create_tables([Contact], safe=True)
    #db.close()


def remove_user(id):
    query = Contact.delete().where(Contact.id == id)
    if query.execute():
        return True
    else:
        return False
