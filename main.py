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

# --- MongoDB connection with fallback ---
def connect_mongo():
    uri = MONGODB_URI
    try:
        client = MongoClient(uri)
        client.admin.command('ping')  # verifica connessione
        print("Connessione a MongoDB riuscita!")
        return client
    except Exception as e:
        print("Errore di connessione MongoDB:", e)
        return None

mongo_client = connect_mongo()
if mongo_client is not None:
    db = mongo_client["discord_bot_db"]
    xp_collection = db["xp_collection"]
else:
    xp_collection = None  # MongoDB non disponibile

# --- CONFIG ---

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

CHANNEL_DAILY = 1388623669886189628
CHANNEL_WEEKLY = 1388623669886189628
CHANNEL_MONTHLY = 1388623669886189628
CHANNEL_LEVELUP = 1383429600016728074

SOCIAL_LINKS = {
    "discord": "https://discord.gg/7xSGy3VQr3",
    "instagram": "https://www.instagram.com/tw3nty.mars/",
    "tiktok": "https://www.tiktok.com/@tw3nty.mars",
    "twitch": "https://www.twitch.tv/tw3ntymars",
    "youtube": "https://www.youtube.com/@tw3ntymars"
}

# --- GLOBAL DATA ---

xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)
user_total_xp = defaultdict(int)
user_cooldowns = {}

last_daily_reset = None
last_weekly_reset = None
last_monthly_reset = None

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# --- XP LOGIC ---

def xp_to_level(xp: int) -> int:
    return int((xp / 50) ** (1/3))

def xp_for_next_level(level: int) -> int:
    return 50 * (level + 1) ** 3

def xp_to_next_level(xp: int) -> int:
    level = xp_to_level(xp)
    next_xp = xp_for_next_level(level)
    return next_xp - xp

def get_next_role(level: int):
    sorted_levels = sorted(ROLE_LEVELS.keys())
    for l in sorted_levels:
        if l > level:
            return l, ROLE_LEVELS[l]
    return None, None

def can_get_xp(user_id: int) -> bool:
    now = datetime.now(TIMEZONE)
    last = user_cooldowns.get(user_id)
    if not last or now - last >= COOLDOWN:
        user_cooldowns[user_id] = now
        return True
    return False

def add_xp(user_id: int, amount: int):
    xp_daily[user_id] += amount
    xp_weekly[user_id] += amount
    xp_monthly[user_id] += amount
    user_total_xp[user_id] += amount

async def check_level_up(user_id: int, member: discord.Member, new_level: int):
    channel = bot.get_channel(CHANNEL_LEVELUP)
    if channel:
        embed = discord.Embed(
            description=f"🎉 {member.mention} è salito al livello **{new_level}**!",
            color=XP_COLOR
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)

    highest_role_level = max([lvl for lvl in ROLE_LEVELS.keys() if lvl <= new_level], default=None)
    if highest_role_level is not None:
        role_id = ROLE_LEVELS[highest_role_level]
        role = member.guild.get_role(role_id)
        if role and role not in member.roles:
            await member.add_roles(role)
            if channel:
                embed = discord.Embed(
                    description=f"🔓 {member.mention} ha sbloccato il ruolo per il **livello {highest_role_level}**!",
                    color=XP_COLOR
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)

# --- DATABASE SAVE / LOAD ---

def convert_keys_to_str(d):
    return {str(k): v for k, v in d.items()}

def save_data():
    if xp_collection is None:
        print("MongoDB non disponibile, dati non salvati.")
        return
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    data = {
        "_id": "xp_data",
        "xp_daily": convert_keys_to_str(dict(xp_daily)),
        "xp_weekly": convert_keys_to_str(dict(xp_weekly)),
        "xp_monthly": convert_keys_to_str(dict(xp_monthly)),
        "user_total_xp": convert_keys_to_str(dict(user_total_xp)),
        "last_daily_reset": last_daily_reset.isoformat() if last_daily_reset else None,
        "last_weekly_reset": last_weekly_reset.isoformat() if last_weekly_reset else None,
        "last_monthly_reset": last_monthly_reset.isoformat() if last_monthly_reset else None
    }
    try:
        xp_collection.replace_one({"_id": "xp_data"}, data, upsert=True)
    except Exception as e:
        print("Errore nel salvataggio dati:", e)

def load_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    if xp_collection is None:
        print("MongoDB non disponibile, carico dati in memoria.")
        now = datetime.now(TIMEZONE)
        last_daily_reset = now
        last_weekly_reset = now
        last_monthly_reset = now
        return

    try:
        data = xp_collection.find_one({"_id": "xp_data"})
    except Exception as e:
        print("Errore nel caricamento dati:", e)
        data = None

    if not data:
        now = datetime.now(TIMEZONE)
        last_daily_reset = now
        last_weekly_reset = now
        last_monthly_reset = now
        return

    for k, v in data.get("xp_daily", {}).items():
        xp_daily[int(k)] = v
    for k, v in data.get("xp_weekly", {}).items():
        xp_weekly[int(k)] = v
    for k, v in data.get("xp_monthly", {}).items():
        xp_monthly[int(k)] = v
    for k, v in data.get("user_total_xp", {}).items():
        user_total_xp[int(k)] = v

    last_daily_reset = datetime.fromisoformat(data.get("last_daily_reset", datetime.now(TIMEZONE).isoformat()))
    last_weekly_reset = datetime.fromisoformat(data.get("last_weekly_reset", datetime.now(TIMEZONE).isoformat()))
    last_monthly_reset = datetime.fromisoformat(data.get("last_monthly_reset", datetime.now(TIMEZONE).isoformat()))

# --- RESET FUNCTIONS ---

def reset_daily():
    global last_daily_reset
    xp_daily.clear()
    last_daily_reset = datetime.now(TIMEZONE)

def reset_weekly():
    global last_weekly_reset
    xp_weekly.clear()
    last_weekly_reset = datetime.now(TIMEZONE)

def reset_monthly():
    global last_monthly_reset
    xp_monthly.clear()
    last_monthly_reset = datetime.now(TIMEZONE)

# --- UTILS ---

def get_position(user_id: int, ranking_dict: dict) -> int | None:
    sorted_list = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(sorted_list, 1):
        if uid == user_id:
            return i
    return None

def get_user_roles(member: discord.Member):
    roles = [role.name for role in member.roles if role.id in ROLE_LEVELS.values()]
    return roles if roles else ["Nessun ruolo"]

# --- EMBED CREATION ---

def create_leaderboard_embed(title: str, ranking_dict: dict):
    embed = discord.Embed(title=title, color=XP_COLOR)
    sorted_list = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    if not sorted_list:
        embed.description = "Nessun dato disponibile."
        return embed
    desc = ""
    for i, (uid, xp) in enumerate(sorted_list, 1):
        desc += f"**{i}.** <@{uid}> — {xp} XP\n"
    embed.description = desc
    embed.set_footer(text=f"Aggiornato: {datetime.now(TIMEZONE).strftime('%d/%m/%Y %H:%M:%S')}")
    return embed

# --- EVENTS & COMMANDS ---

@bot.event
async def on_ready():
    print(f"{bot.user} è online!")
    load_data()
    reset_checks.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    if can_get_xp(user_id):
        old_level = xp_to_level(user_total_xp[user_id])
        gained = random.randint(10, 20)
        add_xp(user_id, gained)
        save_data()
        new_level = xp_to_level(user_total_xp[user_id])

        if new_level > old_level:
            await check_level_up(user_id, message.author, new_level)

    await bot.process_commands(message)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    xp = user_total_xp.get(member.id, 0)
    level = xp_to_level(xp)
    next_level_xp = xp_for_next_level(level)
    xp_needed = next_level_xp - xp

    daily_pos = get_position(member.id, xp_daily) or "N/A"
    weekly_pos = get_position(member.id, xp_weekly) or "N/A"
    monthly_pos = get_position(member.id, xp_monthly) or "N/A"
    global_pos = get_position(member.id, user_total_xp) or "N/A"

    next_role_level, next_role_id = get_next_role(level)
    next_role_name = "Nessun ruolo successivo"
    if next_role_level is not None:
        next_role_name = f"Ruolo livello {next_role_level}"

    embed = discord.Embed(title=f"Classifica di {member.display_name}", color=XP_COLOR)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Livello", value=str(level))
    embed.add_field(name="XP totale", value=str(xp))
    embed.add_field(name="XP per prossimo livello", value=str(xp_needed))
    embed.add_field(name="Posizione Giornaliera", value=str(daily_pos))
    embed.add_field(name="Posizione Settimanale", value=str(weekly_pos))
    embed.add_field(name="Posizione Mensile", value=str(monthly_pos))
    embed.add_field(name="Posizione Globale", value=str(global_pos))
    embed.add_field(name="Prossimo ruolo", value=next_role_name)

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx, timeframe: str = "global"):
    timeframe = timeframe.lower()
    if timeframe == "daily":
        embed = create_leaderboard_embed("Classifica Giornaliera", xp_daily)
    elif timeframe == "weekly":
        embed = create_leaderboard_embed("Classifica Settimanale", xp_weekly)
    elif timeframe == "monthly":
        embed = create_leaderboard_embed("Classifica Mensile", xp_monthly)
    else:
        embed = create_leaderboard_embed("Classifica Globale", user_total_xp)

    await ctx.send(embed=embed)

@tasks.loop(minutes=1)
async def reset_checks():
    now = datetime.now(TIMEZONE)

    global last_daily_reset, last_weekly_reset, last_monthly_reset

    if last_daily_reset is None or now.date() > last_daily_reset.date():
        reset_daily()
        save_data()

    if last_weekly_reset is None or now.isocalendar()[1] > last_weekly_reset.isocalendar()[1]:
        reset_weekly()
        save_data()

    if last_monthly_reset is None or now.month != last_monthly_reset.month:
        reset_monthly()
        save_data()

keep_alive()
bot.run(TOKEN)
