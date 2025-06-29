from pymongo import MongoClient
import discord
from discord.ext import commands, tasks
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

# --- MongoDB connection ---
def connect_mongo():
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print("MongoDB connesso ✅")
        return client
    except Exception as e:
        print("Errore MongoDB:", e)
        return None

mongo_client = connect_mongo()
if mongo_client:
    db = mongo_client["discord_bot_db"]
    xp_collection = db["xp_collection"]
else:
    xp_collection = None

# --- Configurazione ---
TIMEZONE = ZoneInfo("Europe/Rome")
XP_COLOR = 0xB500FF
COOLDOWN = timedelta(minutes=7)

ROLE_LEVELS = {
    0: 1383431607498571796,
    10: 1383433321630924922,
    20: 1383433334343860324,
    40: 1383433340715139244,
    60: 1383433337959481384,
    80: 1386849486948798535,
    100: 1383433343651020904,
}

SOCIAL_LINKS = {
    "discord": "https://discord.gg/7xSGy3VQr3",
    "instagram": "https://www.instagram.com/tw3nty.mars/",
    "tiktok": "https://www.tiktok.com/@tw3nty.mars",
    "twitch": "https://www.twitch.tv/tw3ntymars",
    "youtube": "https://www.youtube.com/@tw3ntymars"
}

CHANNEL_LEVELUP = 1383429600016728074

xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)
user_total_xp = defaultdict(int)
user_cooldowns = {}

last_daily_reset = None
last_weekly_reset = None
last_monthly_reset = None

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# --- Funzioni XP ---
def xp_to_level(xp):
    return int((xp / 50) ** (1/3))

def xp_for_next_level(level):
    return 50 * (level + 1) ** 3

def can_get_xp(user_id):
    now = datetime.now(TIMEZONE)
    last = user_cooldowns.get(user_id)
    if not last or now - last >= COOLDOWN:
        user_cooldowns[user_id] = now
        return True
    return False

def add_xp(user_id, amount):
    xp_daily[user_id] += amount
    xp_weekly[user_id] += amount
    xp_monthly[user_id] += amount
    user_total_xp[user_id] += amount

# --- Salva / Carica ---
def save_data():
    if xp_collection is None:
        return
    data = {
        "_id": "xp_data",
        "xp_daily": dict(xp_daily),
        "xp_weekly": dict(xp_weekly),
        "xp_monthly": dict(xp_monthly),
        "user_total_xp": dict(user_total_xp),
        "last_daily_reset": last_daily_reset.isoformat() if last_daily_reset else None,
        "last_weekly_reset": last_weekly_reset.isoformat() if last_weekly_reset else None,
        "last_monthly_reset": last_monthly_reset.isoformat() if last_monthly_reset else None
    }
    xp_collection.replace_one({"_id": "xp_data"}, data, upsert=True)

def load_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    data = xp_collection.find_one({"_id": "xp_data"}) if xp_collection is not None else None
    if not data:
        now = datetime.now(TIMEZONE)
        last_daily_reset = now
        last_weekly_reset = now
        last_monthly_reset = now
        return
    xp_daily.update({int(k): v for k, v in data.get("xp_daily", {}).items()})
    xp_weekly.update({int(k): v for k, v in data.get("xp_weekly", {}).items()})
    xp_monthly.update({int(k): v for k, v in data.get("xp_monthly", {}).items()})
    user_total_xp.update({int(k): v for k, v in data.get("user_total_xp", {}).items()})
    last_daily_reset = datetime.fromisoformat(data.get("last_daily_reset"))
    last_weekly_reset = datetime.fromisoformat(data.get("last_weekly_reset"))
    last_monthly_reset = datetime.fromisoformat(data.get("last_monthly_reset"))

# --- Eventi ---
@bot.event
async def on_ready():
    print(f"{bot.user} è online!")
    load_data()
    reset_checks.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if can_get_xp(message.author.id):
        old_level = xp_to_level(user_total_xp[message.author.id])
        xp = random.randint(10, 20)
        add_xp(message.author.id, xp)
        save_data()
        new_level = xp_to_level(user_total_xp[message.author.id])
        if new_level > old_level:
            await check_level_up(message.author, new_level)
    await bot.process_commands(message)

# --- Comandi ---
@bot.command()
async def social(ctx):
    embed = discord.Embed(title="🌐 Link Social", color=XP_COLOR)
    for name, link in SOCIAL_LINKS.items():
        embed.add_field(name=name.capitalize(), value=link, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def orario(ctx):
    now = datetime.now(TIMEZONE)
    await ctx.send(f"🕒 Orario attuale: {now.strftime('%H:%M:%S')}")

@bot.command()
async def data(ctx):
    today = datetime.now(TIMEZONE)
    await ctx.send(f"📅 Data di oggi: {today.strftime('%d/%m/%Y')}")

@bot.command()
async def xp(ctx):
    xp = user_total_xp.get(ctx.author.id, 0)
    level = xp_to_level(xp)
    next_level_xp = xp_for_next_level(level)
    await ctx.send(f"Hai {xp} XP (Livello {level}) — te ne servono {next_level_xp - xp} per il prossimo livello.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setxp(ctx, member: discord.Member, amount: int):
    user_total_xp[member.id] = amount
    await ctx.send(f"XP di {member.display_name} impostato a {amount}.")
    save_data()

@bot.command()
@commands.has_permissions(administrator=True)
async def resetxp(ctx, member: discord.Member):
    user_total_xp[member.id] = 0
    await ctx.send(f"XP di {member.display_name} resettato.")
    save_data()

# --- Controllo livello ---
async def check_level_up(member, new_level):
    channel = bot.get_channel(CHANNEL_LEVELUP)
    if channel:
        embed = discord.Embed(description=f"🎉 {member.mention} è salito al livello **{new_level}**!", color=XP_COLOR)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)

# --- Reset automatici ---
@tasks.loop(minutes=1)
async def reset_checks():
    now = datetime.now(TIMEZONE)
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    if now.date() > last_daily_reset.date():
        xp_daily.clear()
        last_daily_reset = now
        save_data()
    if now.isocalendar()[1] > last_weekly_reset.isocalendar()[1]:
        xp_weekly.clear()
        last_weekly_reset = now
        save_data()
    if now.month != last_monthly_reset.month:
        xp_monthly.clear()
        last_monthly_reset = now
        save_data()

keep_alive()
bot.run(TOKEN)
