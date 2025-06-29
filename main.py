import discord
from discord.ext import commands, tasks
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from keep_alive import keep_alive
from pymongo import MongoClient

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["discord_bot_db"]
xp_collection = db["xp_collection"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

    # Gestione ruoli, assegna solo il ruolo più alto raggiunto e non duplicati
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

def save_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
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
    data = xp_collection.find_one({"_id": "xp_data"})
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
    if next_role_id:
        next_role = ctx.guild.get_role(next_role_id)
        if next_role:
            next_role_name = f"{next_role.name} (Lv {next_role_level})"

    roles_names = get_user_roles(member)

    embed = discord.Embed(title=f"📊 Rank di {member.display_name}", color=XP_COLOR)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Livello", value=str(level), inline=True)
    embed.add_field(name="XP Totali", value=str(xp), inline=True)
    embed.add_field(name="XP per prossimo livello", value=str(xp_needed), inline=True)
    embed.add_field(name="Prossimo ruolo", value=next_role_name, inline=False)
    embed.add_field(name="Ruoli attuali", value=", ".join(roles_names), inline=False)
    embed.add_field(name="Posizione Globale", value=str(global_pos), inline=True)
    embed.add_field(name="Posizione Giornaliera", value=str(daily_pos), inline=True)
    embed.add_field(name="Posizione Settimanale", value=str(weekly_pos), inline=True)
    embed.add_field(name="Posizione Mensile", value=str(monthly_pos), inline=True)

    await ctx.send(embed=embed)

@bot.command(name="top")
async def top_command(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Globale Top 10", user_total_xp)
    await ctx.send(embed=embed)

@bot.command()
async def social(ctx):
    embed = discord.Embed(title="Social di Tw3nty Mars", color=XP_COLOR)
    for name, url in SOCIAL_LINKS.items():
        embed.add_field(name=name.capitalize(), value=f"[Link]({url})", inline=True)
    await ctx.send(embed=embed)

@tasks.loop(minutes=10)
async def reset_checks():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    now = datetime.now(TIMEZONE)

    # Reset Giornaliero alle 00:00
    if last_daily_reset.date() < now.date():
        reset_daily()
        save_data()
        channel = bot.get_channel(CHANNEL_DAILY)
        if channel:
            embed = discord.Embed(title="⏰ Reset Giornaliero",
                                  description="La classifica giornaliera è stata resettata!",
                                  color=XP_COLOR)
            await channel.send(embed=embed)

    # Reset Settimanale Lunedì 00:00
    if now.isoweekday() == 1 and (last_weekly_reset.date() < now.date()):
        reset_weekly()
        save_data()
        channel = bot.get_channel(CHANNEL_WEEKLY)
        if channel:
            embed = discord.Embed(title="⏰ Reset Settimanale",
                                  description="La classifica settimanale è stata resettata!",
                                  color=XP_COLOR)
            await channel.send(embed=embed)

    # Reset Mensile il primo giorno del mese 00:00
    if now.day == 1 and (last_monthly_reset.month < now.month or last_monthly_reset.year < now.year):
        reset_monthly()
        save_data()
        channel = bot.get_channel(CHANNEL_MONTHLY)
        if channel:
            embed = discord.Embed(title="⏰ Reset Mensile",
                                  description="La classifica mensile è stata resettata!",
                                  color=XP_COLOR)
            await channel.send(embed=embed)

keep_alive()
bot.run(TOKEN)
