# Import the config
import asyncio

try:
    import config
except ImportError:
    print("Couldn't import config.py! Exiting!")
    exit()

import database
import discord
from discord.ext import commands
from discord import Embed
import os
import aiohttp

URL = "http://localhost:8501/v1/models/toxicity/labels/{label}:predict"
LABEL = "canary"


async def getPrefix(bot, message):
    prefixes = [os.getenv('prefix'), "<@"+str(bot.user.id)+"> ", "<@!"+str(bot.user.id)+"> "]
    return prefixes


bot = commands.Bot(command_prefix=getPrefix, description='HeroAI Bot - https://github.com/HeroGamers/HeroAI',
                   activity=discord.Game(name="with toxic members"), case_insensitive=True)


@bot.event
async def on_connect():
    print("----------[LOGIN SUCESSFULL]----------")
    print("     Username: " + bot.user.name)
    print("     UserID:   " + str(bot.user.id))
    print("--------------------------------------")
    print("\n")

    # Bot done starting up
    print("Bot startup done!\n")


@bot.event
async def on_ready():
    # Bot startup is now done...
    print("HeroAI-Bot has (re)connected to Discord!")

    # For testing purposes, remove on production/final releases
    for guild in bot.guilds:
        database.newGuild(guild.id, guild.name)


@bot.event
async def on_guild_join(guild):
    database.newGuild(guild.id, guild.name)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            embed=Embed(color=discord.Color.red(), description="I need permissions to do that!"))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(
            embed=Embed(color=discord.Color.red(), description="You are missing permissions to do that!"))
    elif isinstance(error, commands.CheckFailure):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        return
    elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
        command = ctx.command
        await ctx.send("```\n" + os.getenv('prefix') + command.name + " " + command.signature + "\n\n" + str(error) +
                       "\n```")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif "User not found!" in str(error):
        await ctx.send("Error: User not found! Try mentioning or using an ID!")
    else:
        await ctx.send("Something went wrong while executing that command... Sorry!")
        print("Command raised an exception!", error, bot)


async def predictToxicity(text):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "HeroAI-Bot", "Accept-Encoding": "gzip",
                       "Content-Type": "application/json"}
            data = {"instances": [[text]]}
            async with session.post(URL.replace("{label}", LABEL), headers=headers, json=data) as response:
                json = await response.json()
                if response.status == 200:
                    try:
                        json_response = json['predictions'][0][0]
                        return json_response
                    except KeyError:
                        print("Error getting JSON for request! - Status code: " +
                                        str(response.status) + " - Response: " + str(json))
                else:
                    print("Error getting request - Status code: " + str(response.status) +
                          " - Response: " + str(json))
    except Exception as e:
        print("Error while predicting toxicity - " + str(e))
    return 0.0


@commands.command(name="setup")
@commands.is_owner()
async def setup(ctx):
    guild = ctx.guild
    channel = ctx.channel

    message = await ctx.send("Which guild do you want to setup?\n"
                   "Currently selected guild: **" + guild.name + "** `("+str(guild.id)+")`\n\n"
                   "✅ This guild.\n"
                   "❎ Another guild.")

    await message.add_reaction("✅")
    await message.add_reaction("❎")

    def check(reaction, user):
        return user == ctx.author and (str(reaction.emoji) == "✅" or str(reaction.emoji) == "❎") and reaction.message.id == message.id

    def check2(msg):
        if msg.author == ctx.author and msg.channel == ctx.channel:
            try:
                int(msg.content)
            except ValueError:
                return False
            return True
        return False

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await message.edit(content="Selection timed out.")
        await message.clear_reactions()
        return
    else:
        await message.clear_reactions()
        if str(reaction.emoji) == "❎":
            await message.edit(content="Which guild do you want to setup?\nType the ID in the chat.")

            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check2)
            except asyncio.TimeoutError:
                await message.edit(content="Selection timed out.")
                return
            else:
                try:
                    await msg.delete()
                except Exception as e:
                    print(str(e))

                guildid = int(msg.content)
                guild = bot.get_guild(guildid)
                if not guild:
                    try:
                        guild = await bot.fetch_guild(guildid)
                    except Exception as e:
                        print(str(e))

                if not guild:
                    await message.edit(content="No guild found matching that ID, sorry.")
                    return
        else:
            await message.edit(content="Which channel do you want to setup?\n"
                               "Currently selected channel: **#" + channel.name + "** `(" + str(channel.id) + ")`\n\n"
                               "✅ This channel.\n"
                               "❎ Another channel.")

            await message.add_reaction("✅")
            await message.add_reaction("❎")

            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await message.edit(content="Selection timed out.")
                await message.clear_reactions()
                return
            else:
                await message.clear_reactions()
                if str(reaction.emoji) == "✅":
                    database.setChannel(guild.id, channel.id)
                    await message.edit(content="**#"+channel.name+"** successfully set as the channel for HeroAI!")
                    return
        await message.edit(content="Currently selected guild: **" + guild.name + "** `("+str(guild.id)+")`\n"
                           "Which channel do you want to setup?\nType the ID in the chat.")

        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check2)
        except asyncio.TimeoutError:
            await message.edit(content="Selection timed out.")
            return
        else:
            try:
                await msg.delete()
            except Exception as e:
                print(str(e))

            channelid = int(msg.content)
            channel = bot.get_channel(channelid)
            if not channel:
                try:
                    channel = await bot.fetch_channel(channelid)
                except Exception as e:
                    print(str(e))

            if not channel:
                await message.edit(content="No channel found matching that ID, sorry.")
                return

            database.setChannel(guild.id, channel.id)
            await message.edit(content="**#"+channel.name+"** successfully set as the channel for HeroAI!")
            return


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    ctx: commands.Context = await bot.get_context(message)

    if ctx.command is not None:
        if isinstance(message.channel, discord.DMChannel):
            print("`%s` (%s) used the `%s` command in their DM's" % (
                ctx.author.name, ctx.author.id, ctx.invoked_with))
        else:
            print("`%s` (%s) used the `%s` command in the guild `%s` (%s), in the channel `%s` (%s)" % (
                ctx.author.name, ctx.author.id, ctx.invoked_with, ctx.guild.name, ctx.guild.id, ctx.channel.name,
                ctx.channel.id))
        await bot.invoke(ctx)
    else:
        member = message.author
        if isinstance(member, discord.Member):
            permissions = member.guild_permissions
            if permissions.administrator or permissions.ban_members or permissions.manage_guild or \
               permissions.manage_messages or permissions.kick_members or permissions.manage_permissions \
               or permissions.manage_roles:
                return

        dbguild = database.getGuild(message.guild.id)
        if dbguild.Channel and isinstance(dbguild.Channel, int):
            channel = None
            try:
                channel = bot.get_channel(dbguild.Channel)
            except Exception as e:
                print(str(e))
            if not channel:
                try:
                    channel = await bot.fetch_channel(dbguild.Channel)
                except Exception as e:
                    print(str(e))

            if channel:
                toxicity = await predictToxicity(message.content)

                print("["+str(round(toxicity*100, 2))+"%] <"+message.author.name+"> " + message.content)

                db_message = database.newMessage(message.id, toxicity, message.guild.id, message.channel.id, message.author.id, message.content)

                if int(toxicity*100) >= db_message.Guild.MinimumToxicity:
                    color = discord.Color.red()
                    if toxicity*100 <= 60.0:
                        if toxicity*100 <= 30.0:
                            color = discord.Color.green()
                        else:
                            color = discord.Color.orange()
                    embed = Embed(color=color, title="["+str(int(round(toxicity*100, 0)))+"%] Toxic Message")
                    embed.add_field(name="Message Content", value=message.content[:200], inline=False)
                    embed.add_field(name="Author", value=member.name + " ("+str(member.id)+")", inline=True)
                    embed.add_field(name="Channel", value="#"+str(message.channel.name), inline=True)
                    embed.add_field(name="Exact Toxicity", value=str(toxicity), inline=True)
                    embed.add_field(name="Message Link", value="[Click me](https://discord.com/channels/"+str(message.guild.id)+"/"+str(message.channel.id)+"/"+str(message.id)+")", inline=True)
                    await channel.send(embed=embed)


if __name__ == '__main__':
    bot.add_command(setup)
    bot.load_extension("jishaku")

bot.run(os.getenv('token'))
