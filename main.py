import discord
from discord.ext import commands, tasks
import datetime
import os
from zoneinfo import ZoneInfo
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    await bot.wait_until_ready()
    buongiorno.start()
    buonanotte.start()
    compleanno.start()

@tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=ZoneInfo("Europe/Rome")))
async def buongiorno():
    try:
        canale = await bot.fetch_channel(CHANNEL_ID)
        await canale.send("Buongiorno belli, come state? Buona giornata! 🌞 @everyone")
    except Exception as e:
        print(f"❌ Errore invio buongiorno: {e}")

@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("Europe/Rome")))
async def buonanotte():
    try:
        canale = await bot.fetch_channel(CHANNEL_ID)
        await canale.send("Buonanotte belli, a domani, dormite bene! 🌝 @everyone")
    except Exception as e:
        print(f"❌ Errore invio buonanotte: {e}")

@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("Europe/Rome")))
async def compleanno():
    now = datetime.datetime.now(ZoneInfo("Europe/Rome"))
    print(f"Controllo compleanno: {now}")
    if now.month == 6 and now.day == 20:
        try:
            canale = await bot.fetch_channel(CHANNEL_ID)
            await canale.send("@everyone È IL COMPLEANNO DI <@734059577078972566> RIEMPITE IL SERVER CON MESSAGGI DI AUGURI! 🥰")
            compleanno.cancel()
        except Exception as e:
            print(f"Errore invio compleanno: {e}")

@compleanno.before_loop
async def before_compleanno():
    await bot.wait_until_ready()

keep_alive()
bot.run(TOKEN)

