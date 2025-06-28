import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo  # Python 3.9+
import json
import asyncio

from keep_alive import keep_alive  # Assumi che il tuo keep_alive funzioni

print("Installing dependencies from requirements.txt")
print("...")
print("Running python main.py")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_DAILY = 1388623669886189628
CHANNEL_WEEKLY = 1388623669886189628
CHANNEL_MONTHLY = 1388623669886189628
CHANNEL_LEVELUP = 1383429600016728074

ROLE_LEVELS = {
    0: 11383431607498571796,
    10: 1383433321630924922,
    20: 1383433334343860324,
    40: 1383433340715139244,
    60: 1383433337959481384,
    80: 1386849486948798535,
    100: 1383433343651020904,
}

XP_COLOR = 0xB500FF
TIMEZONE = ZoneInfo("Europe/Rome")

xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)

last_daily_reset = datetime.now(TIMEZONE)
last_weekly_reset = datetime.now(TIMEZONE)
last_monthly_reset = datetime.now(TIMEZONE)

scheduler = AsyncIOScheduler()
XP_FILE = "xp_data.json"

def save_xp():
    with open(XP_FILE, "w") as f:
        json.dump({
            "daily": dict(xp_daily),
            "weekly": dict(xp_weekly),
            "monthly": dict(xp_monthly),
        }, f)

def load_xp():
    if os.path.exists(XP_FILE):
        try:
            with open(XP_FILE, "r") as f:
                data = json.load(f)
                xp_daily.update({int(k): v for k, v in data.get("daily", {}).items()})
                xp_weekly.update({int(k): v for k, v in data.get("weekly", {}).items()})
                xp_monthly.update({int(k): v for k, v in data.get("monthly", {}).items()})
                print("✅ XP caricati da file")
        except Exception as e:
            print(f"⚠️ Errore nel caricamento XP: {e}")

async def periodic_save():
    while True:
        await asyncio.sleep(30)  # ogni 30 secondi
        save_xp()

def check_resets():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    now = datetime.now(TIMEZONE)

    if (now - last_daily_reset) > timedelta(days=1):
        xp_daily.clear()
        last_daily_reset = now

    if now.isocalendar()[1] != last_weekly_reset.isocalendar()[1]:
        xp_weekly.clear()
        last_weekly_reset = now

    if now.month != last_monthly_reset.month:
        xp_monthly.clear()
        last_monthly_reset = now

def add_xp(user_id):
    xp_daily[user_id] += 10
    xp_weekly[user_id] += 10
    xp_monthly[user_id] += 10

async def update_roles(member, total_xp):
    guild = member.guild
    eligible_roles = [(xp_req, role_id) for xp_req, role_id in ROLE_LEVELS.items() if total_xp >= xp_req]
    if not eligible_roles:
        return
    max_xp_req, role_id_to_add = max(eligible_roles, key=lambda x: x[0])
    role_to_add = guild.get_role(role_id_to_add)
    if not role_to_add or role_to_add in member.roles:
        return

    try:
        await member.add_roles(role_to_add, reason="Aggiornamento ruolo XP")
        print(f"Ruolo {role_to_add.name} assegnato a {member.display_name}")
        channel = guild.get_channel(CHANNEL_LEVELUP)
        if channel:
            embed = discord.Embed(
                title="🎉 Nuovo livello raggiunto!",
                description=f"{member.mention} ha raggiunto il ruolo **{role_to_add.name}**!",
                color=XP_COLOR,
                timestamp=datetime.now(TIMEZONE)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Errore assegnazione ruolo: {e}")

def create_leaderboard_embed(title, xp_dict, guild):
    top = sorted(xp_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title=title, color=XP_COLOR)
    if not top:
        embed.description = "Nessun dato disponibile."
        return embed
    for i, (user_id, xp) in enumerate(top, start=1):
        member = guild.get_member(user_id)
        name = member.display_name if member else f"Utente sconosciuto ({user_id})"
        embed.add_field(name=f"#{i} - {name}", value=f"XP: {xp}", inline=False)
    return embed

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.type == discord.ChannelType.private:
        return

    now = datetime.now(TIMEZONE)
    msg_time = message.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(TIMEZONE)
    if (now - msg_time).total_seconds() > 300:  # ignora messaggi più vecchi di 5 minuti
        return

    check_resets()
    add_xp(message.author.id)
    total_xp = xp_monthly[message.author.id]
    await update_roles(message.author, total_xp)
    await bot.process_commands(message)

async def send_leaderboards():
    for guild in bot.guilds:
        ch_daily = guild.get_channel(CHANNEL_DAILY)
        ch_weekly = guild.get_channel(CHANNEL_WEEKLY)
        ch_monthly = guild.get_channel(CHANNEL_MONTHLY)
        if not all([ch_daily, ch_weekly, ch_monthly]):
            print(f"Canali non trovati in {guild.name}")
            continue
        try:
            await ch_daily.send(embed=create_leaderboard_embed("🏆 Classifica Giornaliera XP", xp_daily, guild))
            await ch_weekly.send(embed=create_leaderboard_embed("🏆 Classifica Settimanale XP", xp_weekly, guild))
            await ch_monthly.send(embed=create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, guild))
        except Exception as e:
            print(f"Errore invio classifica in {guild.name}: {e}")

# Comandi

@bot.command(name="testxp")
async def test_xp(ctx):
    user_id = ctx.author.id
    xp_daily[user_id] += 100
    xp_weekly[user_id] += 100
    xp_monthly[user_id] += 100
    total_xp = xp_monthly[user_id]
    await update_roles(ctx.author, total_xp)
    await ctx.send(f"🎉 {ctx.author.display_name}, ti ho aggiunto 100 XP! Totale mensile: {total_xp}")

@bot.command(name="classifica")
async def classifica(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="day")
async def day(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Giornaliera XP", xp_daily, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="week")
async def week(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Settimanale XP", xp_weekly, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="month")
async def month(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = member.id

    total_xp = xp_monthly.get(user_id, 0)
    guild = ctx.guild

    # Calcola posizione in classifica mensile
    sorted_xp = sorted(xp_monthly.items(), key=lambda x: x[1], reverse=True)
    position = None
    for i, (uid, xp) in enumerate(sorted_xp, start=1):
        if uid == user_id:
            position = i
            break
    if position is None:
        position = "Non classificato"

    embed = discord.Embed(
        title=f"📊 Statistiche XP di {member.display_name}",
        color=XP_COLOR,
        timestamp=datetime.now(TIMEZONE)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="XP Mensile", value=str(total_xp))
    embed.add_field(name="Posizione in classifica", value=str(position))
    await ctx.send(embed=embed)

# --- COMANDO RESET XP e RUOLI ---
@bot.command(name="resetxp")
@commands.has_permissions(administrator=True)
async def reset_xp(ctx):
    xp_daily.clear()
    xp_weekly.clear()
    xp_monthly.clear()
    save_xp()

    # Rimuovi ruoli XP da tutti i membri
    for member in ctx.guild.members:
        roles_to_remove = []
        for xp_req, role_id in ROLE_LEVELS.items():
            role = ctx.guild.get_role(role_id)
            if role in member.roles:
                roles_to_remove.append(role)
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Reset XP e ruoli")
            except Exception as e:
                print(f"Errore rimuovendo ruoli da {member.display_name}: {e}")

    await ctx.send("✅ XP e ruoli resettati per tutti! Ora puoi riassegnare i ruoli manualmente e ricominciare da zero.")

# Social
# (Tutti i tuoi comandi social qui... lasciati invariati)

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    scheduler.add_job(send_leaderboards, 'cron', day_of_week='mon', hour=8, minute=0)
    scheduler.start()
    asyncio.create_task(periodic_save())

if __name__ == "__main__":
    load_xp()
    keep_alive()
    bot.run(TOKEN)
