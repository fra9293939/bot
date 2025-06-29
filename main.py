import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import os
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo

from keep_alive import keep_alive  # Assicurati che funzioni correttamente

# === CONFIGURAZIONE BOT ===
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === COSTANTI / ID ===
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

# === VARIABILI XP ===
xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)
last_daily_reset = datetime.now(TIMEZONE)
last_weekly_reset = datetime.now(TIMEZONE)
last_monthly_reset = datetime.now(TIMEZONE)

scheduler = AsyncIOScheduler()

# === FUNZIONI XP ===
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

def add_xp(user_id, amount=10):
    xp_daily[user_id] += amount
    xp_weekly[user_id] += amount
    xp_monthly[user_id] += amount

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

# === EVENTI ===
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.type == discord.ChannelType.private:
        return
    check_resets()
    add_xp(message.author.id)
    total_xp = xp_monthly[message.author.id]
    await update_roles(message.author, total_xp)
    await bot.process_commands(message)

# === COMANDI XP ===
# ... (comandi come test_xp, set_xp, rank, classifica, twitch, youtube, ecc.)
# (tutto invariato come da tuo messaggio, già incluso correttamente)

# === COMANDO SEND ===
@bot.command(name="send")
async def send(ctx, *, message=None):
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Non hai i permessi per usare questo comando.")
        return

    files = []
    if ctx.message.attachments:
        try:
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
        except Exception as e:
            await ctx.send(f"❌ Errore caricamento allegati: {e}")
            return

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ Non ho i permessi per eliminare il messaggio.")
        return
    except Exception as e:
        await ctx.send(f"⚠️ Errore eliminazione messaggio: {e}")
        return

    if message or files:
        await ctx.send(content=message, files=files)
    else:
        await ctx.send("⚠️ Nessun messaggio o allegato da inviare.")

# ✅ UNICO on_ready
@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    scheduler.add_job(send_leaderboards, 'cron', day_of_week='mon', hour=8, minute=0, timezone=TIMEZONE)
    scheduler.start()

# === AVVIO ===
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)

