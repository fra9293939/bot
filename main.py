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

@bot.command(name="twitch")
async def twitch(ctx):
    embed = discord.Embed(
        title="🎮 Twitch di Tw3nty Mars",
        description="[Clicca qui per visitare il canale Twitch](https://www.twitch.tv/tw3nty_mars?sr=a)",
        color=0xB500FF
    )
    embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
    await ctx.send(embed=embed)

@bot.command(name="youtube", aliases=["yt"])
async def youtube(ctx):
    embed = discord.Embed(
        title="▶️ Canale YouTube di Tw3nty Mars",
        description="[Guarda i video qui](https://www.youtube.com/channel/UC6E0F7DUBbF2ZP6GRV8cHFg)",
        color=0xB500FF
    )
    embed.set_thumbnail(url="https://www.youtube.com/s/desktop/6ee67e1a/img/favicon_32.png")
    await ctx.send(embed=embed)

@bot.command(name="tiktok")
async def tiktok(ctx):
    embed = discord.Embed(
        title="📱 TikTok di Tw3nty Mars",
        description=(
            "Profilo per le live: [tw3ntymars](https://www.tiktok.com/@tw3ntymars)\n"
            "Profilo personale: [martinaastasi](https://www.tiktok.com/@martinaastasi)"
        ),
        color=0xB500FF
    )
    await ctx.send(embed=embed)

@bot.command(name="instagram", aliases=["ig"])
async def instagram(ctx):
    embed = discord.Embed(
        title="📸 Instagram di Tw3nty Mars",
        description="[Visita il profilo Instagram](https://www.instagram.com/tw3nty_mars)",
        color=0xB500FF
    )
    await ctx.send(embed=embed)

@bot.command(name="discord", aliases=["ds"])
async def discord_cmd(ctx):
    embed = discord.Embed(
        title="💬 Server Discord",
        description="[Unisciti qui!](https://discord.gg/xKqWsTYRqy)",
        color=0xB500FF
    )
    await ctx.send(embed=embed)

@bot.command(name="orari")
async def orari(ctx):
    embed = discord.Embed(
        title="📅 Streaming Schedule",
        description="TUTTI I GIORNI DALLE 20:30 ALLE 23:30! 🕑\n(salvo imprevisti, vi avvisiamo su IG e Discord)",
        color=0xB500FF
    )
    await ctx.send(embed=embed)

@bot.command(name="comandi")
async def comandi(ctx):
    embed = discord.Embed(
        title="📜 Lista comandi",
        description=(
            "!twitch - Link Twitch\n"
            "!youtube / !yt - Link YouTube\n"
            "!tiktok - Link TikTok\n"
            "!instagram / !ig - Link Instagram\n"
            "!discord / !ds - Link Discord\n"
            "!orari - Orario streaming\n"
            "!comandi - Questa lista"
        ),
        color=0xB500FF
    )
    await ctx.send(embed=embed)

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
