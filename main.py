import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo  # per gestire i fusi orari

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Canali classifica (modifica con i tuoi ID)
CHANNEL_DAILY = 1388623669886189628
CHANNEL_WEEKLY = 1388623669886189628  # stesso canale o cambia
CHANNEL_MONTHLY = 1388623669886189628

# Canale per messaggi level up (modifica con tuo ID)
CHANNEL_LEVELUP = 1383429600016728074

XP_COLOR = 0xB500FF

# XP in memoria
xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)

# Settiamo l'ora di Roma per i reset
TIMEZONE = ZoneInfo("Europe/Rome")

last_daily_reset = datetime.now(TIMEZONE)
last_weekly_reset = datetime.now(TIMEZONE)
last_monthly_reset = datetime.now(TIMEZONE)

# Mappa ruoli e livelli (modifica con i tuoi ID reali)
ROLE_LEVELS = {
    0: 11383431607498571796,        # Ruolo base
    10: 1383433321630924922,        # Livello 10
    20: 1383433334343860324,        # Livello 20
    40: 1383433340715139244,        # Livello 40
    60: 1383433337959481384,        # Livello 60
    80: 1386849486948798535,        # Livello 80
    100: 1383433343651020904,       # Livello 100
}

def reset_xp():
    global xp_daily, xp_weekly, xp_monthly
    xp_daily.clear()
    xp_weekly.clear()
    xp_monthly.clear()

def check_resets():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    now = datetime.now(TIMEZONE)
    
    # Reset giornaliero dopo 1 giorno
    if (now - last_daily_reset) > timedelta(days=1):
        xp_daily.clear()
        last_daily_reset = now
    
    # Reset settimanale se cambia settimana ISO
    if now.isocalendar()[1] != last_weekly_reset.isocalendar()[1]:
        xp_weekly.clear()
        last_weekly_reset = now
    
    # Reset mensile se cambia mese
    if now.month != last_monthly_reset.month:
        xp_monthly.clear()
        last_monthly_reset = now

async def update_roles(member, total_xp):
    guild = member.guild

    # Trova il ruolo più alto che l'utente può avere con XP attuale
    eligible_roles = [(xp_req, role_id) for xp_req, role_id in ROLE_LEVELS.items() if total_xp >= xp_req]
    if not eligible_roles:
        return

    max_xp_req, role_id_to_add = max(eligible_roles, key=lambda x: x[0])
    role_to_add = guild.get_role(role_id_to_add)
    if not role_to_add:
        return

    if role_to_add in member.roles:
        return

    try:
        await member.add_roles(role_to_add, reason="Aggiornamento ruolo per XP")
        print(f"Ruolo {role_to_add.name} assegnato a {member.display_name}")

        # Manda messaggio congratulazioni nel canale level up
        levelup_channel = guild.get_channel(CHANNEL_LEVELUP)
        if levelup_channel:
            embed = discord.Embed(
                title="🎉 Complimenti! Nuovo livello raggiunto!",
                description=f"{member.mention} ha raggiunto il ruolo **{role_to_add.name}**!",
                color=XP_COLOR,
                timestamp=datetime.now(TIMEZONE)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await levelup_channel.send(embed=embed)
    except Exception as e:
        print(f"Errore assegnazione ruolo a {member.display_name}: {e}")

def add_xp(user_id):
    xp_daily[user_id] += 10
    xp_weekly[user_id] += 10
    xp_monthly[user_id] += 10

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.type == discord.ChannelType.private:
        return

    check_resets()
    add_xp(message.author.id)

    total_xp = xp_monthly[message.author.id]
    member = message.author
    await update_roles(member, total_xp)

    await bot.process_commands(message)

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

@tasks.loop(minutes=5)
async def send_leaderboards():
    for guild in bot.guilds:
        ch_daily = guild.get_channel(CHANNEL_DAILY)
        ch_weekly = guild.get_channel(CHANNEL_WEEKLY)
        ch_monthly = guild.get_channel(CHANNEL_MONTHLY)

        if not all([ch_daily, ch_weekly, ch_monthly]):
            print(f"Uno o più canali non trovati nel server {guild.name}")
            continue

        try:
            await ch_daily.send(embed=create_leaderboard_embed("🏆 Classifica Giornaliera XP", xp_daily, guild))
            await ch_weekly.send(embed=create_leaderboard_embed("🏆 Classifica Settimanale XP", xp_weekly, guild))
            await ch_monthly.send(embed=create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, guild))
        except Exception as e:
            print(f"Errore invio classifica in {guild.name}: {e}")

@bot.command(name="testxp")
async def test_xp(ctx):
    user_id = ctx.author.id

    # Aggiunge 100 XP (giornalieri, settimanali e mensili) per test
    xp_daily[user_id] += 100
    xp_weekly[user_id] += 100
    xp_monthly[user_id] += 100

    # Aggiorna i ruoli basandosi sull'XP mensile
    total_xp = xp_monthly[user_id]
    await update_roles(ctx.author, total_xp)

    await ctx.send(f"🎉 {ctx.author.display_name}, ti ho aggiunto 100 XP e aggiornato i ruoli! XP totali mensili: {total_xp}")

@bot.command(name="classifica")
async def classifica(ctx):
    # Mostra la classifica mensile nel canale dove viene invocato
    embed = create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, ctx.guild)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot pronto come {bot.user}")
    send_leaderboards.start()

bot.run(TOKEN)

