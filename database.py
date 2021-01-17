import pymysql
from peewee import SqliteDatabase, Model, CharField, MySQLDatabase, InternalError, ForeignKeyField, \
    BigIntegerField, FloatField, IntegerField
import datetime
import os

# This file mostly consists of different, quite identical, calls to the database, and as such functions look quite
# alike. For this reason, the "issues" with duplicates are ignored from this file on Code Climate.

# Initiation of database
if os.getenv('db_type') is not None and os.getenv('db_type').upper() == "MYSQL":
    host = "localhost"
    if os.getenv('db_host'):
        host = os.getenv('db_host')
    else:
        print("Database host is empty, using " + host + " as host...")

    user = "root"
    if os.getenv('db_user'):
        user = os.getenv('db_user')
    else:
        print("Database user is empty, using " + user + " as user...")

    port = "3306"
    if os.getenv('db_port'):
        port = os.getenv('db_port')
    else:
        print("Database port is empty, using " + port + " as port...")

    db = MySQLDatabase('heroaibot', user=user, password=os.getenv('db_pword'), host=host,
                       port=int(port))

    # Check for possible connection issues to the db
    try:
        db.connection()
    except Exception as e:
        if "Can't connect" in str(e):
            print("An error occured while trying to connect to the MySQL Database: " + str(e) + ". Using flatfile...")
            db = SqliteDatabase('./HeroAIBot.db')
        elif "Unknown database" in str(e):
            print("An error occured while trying to connect to the MySQL Database: " + str(e) +
                  ". Trying to create database...")
            try:
                conn = pymysql.connect(host=host, user=user, password=os.getenv('db_pword'), port=int(port))
                conn.cursor().execute('CREATE DATABASE heroaibot')
                conn.close()
                print("Created Database!")
            except Exception as e:
                print("An error occured while trying to create the heroaibot Database: " + str(e) + ". Using flatfile...")
                db = SqliteDatabase('./HeroAIBot.db')
    except InternalError as e:
        print("An error occured while trying to use the MySQL Database: " + str(e) + ". Mi...")
        db = SqliteDatabase('./HeroAIBot.db')
else:
    print("Database type is not set to MYSQL, using flatfile...")
    db = SqliteDatabase('./HeroAIBot.db')

# Constant variables
snowflake_max_length = 20  # It is currently 18, but max size of uint64 is 20 chars
discordtag_max_length = 37  # Max length of usernames are 32 characters, added # and the discrim gives 37
guildname_max_length = 100  # For some weird reason guild names can be up to 100 chars...
message_max_length = 2000  # The length a message can be
discord_epoch = 1420070400000  # The Discord Epoch
messages_keep = 30*86400000.0  # The amount of time to keep messages, in milliseconds (used for UNIX time)

# ------------------------------------------ CUSTOM CONFIGS FOR GUILDS ------------------------------------------ #


# The Guilds Table
class guilds(Model):
    GuildID = BigIntegerField(primary_key=True, unique=True)
    Name = CharField(max_length=guildname_max_length)
    MinimumToxicity = IntegerField(default=50)
    Channel = BigIntegerField(null=True)

    class Meta:
        database = db


# Adding new guild to the DB
def newGuild(guildid, name):
    try:
        guild = guilds.create(GuildID=guildid, Name=name)
        return guild
    except Exception as error:
        print("Error doing new guild - " + str(error), "ERROR")
        return False


# Get a guild from the DB
def getGuild(guildid):
    query = guilds.select().where(guilds.GuildID == guildid)
    if query.exists():
        return query[0]
    return False


# Get all guilds from the DB
def getGuilds():
    query = guilds.select()
    if query.exists():
        return query
    return []


# Set an announcement channel for new matches for a guild
def setChannel(guildid, channelid):
    query = guilds.update(Channel=channelid).where(guilds.GuildID == guildid)
    query.execute()


# Removes an announcement channel from a guild
def removeChannel(guildid):
    query = guilds.update(Channel=None).where(guilds.GuildID == guildid)
    query.execute()


# ------------------------------------------ USERS TABLE ------------------------------------------ #


# The Users Table
class users(Model):
    UserID = BigIntegerField(primary_key=True, unique=True)
    DiscordTag = CharField(max_length=discordtag_max_length, null=True)

    class Meta:
        database = db


# Add user
def newUser(userid, discordtag=None):
    try:
        user = users.create(UserID=userid, DiscordTag=discordtag)
        return user
    except Exception as error:
        print("Error doing new user - " + str(error), "ERROR")
        return False


# Get user from userid
def getUser(userid):
    query = users.select().where(users.UserID == userid)
    if query.exists():
        return query[0]
    else:
        return newUser(userid)


# Update DiscordTag
def updateUser(user, discordtag):
    query = users.update(DiscordTag=discordtag).where(users.UserID == user.UserID)
    query.execute()


# ------------------------------------------ MESSAGES TABLE ------------------------------------------ #


# The Messages Table, for user-sent messages
class messages(Model):
    MessageID = BigIntegerField(primary_key=True, unique=True)
    Toxicity = FloatField(default=0.0, null=True)
    Content = CharField(max_length=2000, null=True)
    Guild = ForeignKeyField(guilds, backref='messages')
    ChannelID = BigIntegerField()
    Author = ForeignKeyField(users, backref='messages')

    class Meta:
        database = db


# Adds a new message to the database
def newMessage(messageid, toxicity, guildid, channelid, authorid, content=None):
    try:
        message = messages.create(MessageID=messageid, Toxicity=toxicity, Guild=getGuild(guildid), ChannelID=channelid, Content=content,
                                  Author=getUser(authorid))
        return message
    except Exception as error:
        print("Error doing new message - " + str(error), "ERROR")
        return False


# Gets a datetime object for the time of the message
def getMessage(messageid):
    query = messages.select().where(messages.MessageID == messageid)
    if query.exists():
        return query[0]
    return None


# Puts new content in message, after edit, for example
def updateMessage(message, content):
    query = messages.update(Content=content).where(messages.MessageID == message.MessageID)
    query.execute()


# Clears old messages
def clearOldMessages():
    keepTime = messages_keep
    now_unix = datetime.datetime.now().timestamp()
    # Delete messages that are older than x amount of time, defined in top of DB script
    query = messages.delete().where(((messages.MessageID >> 22)+discord_epoch)+keepTime >= now_unix)
    messages_removed = query.execute()
    return messages_removed

# -------------------------------------------------- SETUP OF TABLES ------------------------------------------------- #


def create_tables():
    with db:
        db.create_tables([guilds, messages, users])


create_tables()
