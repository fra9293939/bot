import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from pymongo import MongoClient

# --- CONFIG ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
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

CHANNEL_LEVELUP = 1383429600016728074

# --- GLOBAL STATE ---
xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)
user_total_xp = defaultdict(int)
user_cooldowns = {}

last_daily_reset = None
last_weekly_reset = None
last_monthly_reset = None

# --- MONGO CONNECT ---
def connect_mongo():
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print("MongoDB connesso.")
        return client
    except Exception as e:
        print("MongoDB errore:", e)
        return None

mongo_client = connect_mongo()
xp_collection = mongo_client["discord_bot_db"]["xp_collection"] if mongo_client else None

# --- DISCORD SETUP ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- XP SYSTEM ---
def xp_to_level(xp): return int((xp / 50) ** (1/3))
def xp_for_next_level(level): return 50 * (level + 1) ** 3

def can_get_xp(uid):
    now = datetime.now(TIMEZONE)
    if uid not in user_cooldowns or now - user_cooldowns[uid] >= COOLDOWN:
        user_cooldowns[uid] = now
        return True
    return False

def add_xp(uid, amount):
    xp_daily[uid] += amount
    xp_weekly[uid] += amount
    xp_monthly[uid] += amount
    user_total_xp[uid] += amount

def get_next_role(level):
    for l in sorted(ROLE_LEVELS):
        if l > level:
            return l, ROLE_LEVELS[l]
    return None, None

async def check_level_up(uid, member, new_level):
    ch = bot.get_channel(CHANNEL_LEVELUP)
    if ch:
        embed = discord.Embed(description=f"🎉 {member.mention} ha raggiunto il livello **{new_level}**!", color=XP_COLOR)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ch.send(embed=embed)

    for lvl in sorted(ROLE_LEVELS, reverse=True):
        if lvl <= new_level:
            role = member.guild.get_role(ROLE_LEVELS[lvl])
            if role and role not in member.roles:
                await member.add_roles(role)
                if ch:
                    await ch.send(f"🔓 {member.mention} ha sbloccato il ruolo di livello {lvl}!")
            break

# --- RESET + DB ---
def reset_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    xp_daily.clear(); xp_weekly.clear(); xp_monthly.clear()
    now = datetime.now(TIMEZONE)
    last_daily_reset = last_weekly_reset = last_monthly_reset = now

def save_data():
    if not xp_collection: return
    data = {
        "_id": "xp_data",
        "xp_daily": dict(xp_daily),
        "xp_weekly": dict(xp_weekly),
        "xp_monthly": dict(xp_monthly),
        "user_total_xp": dict(user_total_xp),
        "last_daily_reset": last_daily_reset.isoformat(),
        "last_weekly_reset": last_weekly_reset.isoformat(),
        "last_monthly_reset": last_monthly_reset.isoformat(),
    }
    xp_collection.replace_one({"_id": "xp_data"}, data, upsert=True)

def load_data():
    if not xp_collection: return reset_data()
    data = xp_collection.find_one({"_id": "xp_data"})
    if not data: return reset_data()
    xp_daily.update({int(k): v for k, v in data.get("xp_daily", {}).items()})
    xp_weekly.update({int(k): v for k, v in data.get("xp_weekly", {}).items()})
    xp_monthly.update({int(k): v for k, v in data.get("xp_monthly", {}).items()})
    user_total_xp.update({int(k): v for k, v in data.get("user_total_xp", {}).items()})
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    last_daily_reset = datetime.fromisoformat(data.get("last_daily_reset"))
    last_weekly_reset = datetime.fromisoformat(data.get("last_weekly_reset"))
    last_monthly_reset = datetime.fromisoformat(data.get("last_monthly_reset"))

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f"{bot.user} è online!")
    load_data()
    reset_check.start()

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    print(f"[DEBUG] Messaggio: {msg.content}")
    uid = msg.author.id
    if can_get_xp(uid):
        before = xp_to_level(user_total_xp[uid])
        gained = random.randint(10, 20)
        add_xp(uid, gained)
        after = xp_to_level(user_total_xp[uid])
        save_data()
        if after > before:
            await check_level_up(uid, msg.author, after)
    await bot.process_commands(msg)

# --- COMMANDS ---
@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    xp = user_total_xp.get(member.id, 0)
    level = xp_to_level(xp)
    next_xp = xp_for_next_level(level)
    embed = discord.Embed(title=f"Profilo di {member.display_name}", color=XP_COLOR)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Livello", value=str(level))
    embed.add_field(name="XP", value=f"{xp}/{next_xp}")
    pos = sorted(user_total_xp.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(pos, 1):
        if uid == member.id:
            embed.add_field(name="Posizione Globale", value=str(i))
            break
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    embed = discord.Embed(title="Top 10 XP", color=XP_COLOR)
    top = sorted(user_total_xp.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (uid, xp) in enumerate(top, 1):
        embed.add_field(name=f"{i}.", value=f"<@{uid}>: {xp} XP", inline=False)
    await ctx.send(embed=embed)

# --- RESET CHECK ---
@tasks.loop(minutes=1)
async def reset_check():
    now = datetime.now(TIMEZONE)
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    if last_daily_reset.date() < now.date(): xp_daily.clear(); last_daily_reset = now
    if last_weekly_reset.isocalendar()[1] < now.isocalendar()[1]: xp_weekly.clear(); last_weekly_reset = now
    if last_monthly_reset.month < now.month: xp_monthly.clear(); last_monthly_reset = now
    save_data()

# --- RUN ---
bot.run(TOKEN)
