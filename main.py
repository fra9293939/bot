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

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    scheduler.add_job(send_leaderboards, 'cron', day_of_week='mon', hour=8, minute=0, timezone=TIMEZONE)
    scheduler.start()

# === COMANDI XP ===
@bot.command(name="testxp")
async def test_xp(ctx):
    user_id = ctx.author.id
    add_xp(user_id, 100)
    total_xp = xp_monthly[user_id]
    await update_roles(ctx.author, total_xp)
    await ctx.send(f"🎉 {ctx.author.display_name}, ti ho aggiunto 100 XP! Totale mensile: {total_xp}")

@bot.command(name="setxp")
@commands.has_permissions(administrator=True)
async def set_xp(ctx):
    await ctx.send("Inserisci quanti XP vuoi aggiungere (numero intero positivo):")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    try:
        msg = await bot.wait_for('message', check=check, timeout=30)
        xp_to_add = int(msg.content)
        if xp_to_add <= 0:
            await ctx.send("Per favore inserisci un numero positivo.")
            return
    except asyncio.TimeoutError:
        await ctx.send("⏰ Timeout: non hai risposto in tempo.")
        return

    user_id = ctx.author.id
    add_xp(user_id, xp_to_add)
    total_xp = xp_monthly[user_id]
    await update_roles(ctx.author, total_xp)
    await ctx.send(f"🎉 {ctx.author.display_name}, ti ho aggiunto {xp_to_add} XP! Totale mensile: {total_xp}")

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = member.id
    guild = ctx.guild

    def get_position(xp_dict):
        sorted_xp = sorted(xp_dict.items(), key=lambda x: x[1], reverse=True)
        for i, (uid, xp) in enumerate(sorted_xp, start=1):
            if uid == user_id:
                return i
        return None

    daily_xp = xp_daily.get(user_id, 0)
    weekly_xp = xp_weekly.get(user_id, 0)
    monthly_xp = xp_monthly.get(user_id, 0)

    daily_pos = get_position(xp_daily) or "Non classificato"
    weekly_pos = get_position(xp_weekly) or "Non classificato"
    monthly_pos = get_position(xp_monthly) or "Non classificato"

    total_xp = monthly_xp

    sorted_levels = sorted(ROLE_LEVELS.keys())
    next_level_xp = None
    next_level_role = None
    for lvl in sorted_levels:
        if lvl > total_xp:
            next_level_xp = lvl
            next_level_role = guild.get_role(ROLE_LEVELS[lvl])
            break

    xp_to_next_level = next_level_xp - total_xp if next_level_xp else 0

    roles_have = []
    roles_next = []
    for xp_req, role_id in sorted(ROLE_LEVELS.items()):
        role = guild.get_role(role_id)
        if role in member.roles:
            roles_have.append(role.name)
        elif xp_req > total_xp:
            roles_next.append(role.name)

    embed = discord.Embed(
        title=f"📊 Statistiche XP di {member.display_name}",
        color=XP_COLOR,
        timestamp=datetime.now(TIMEZONE)
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="XP Giornalieri", value=str(daily_xp), inline=True)
    embed.add_field(name="Posizione Giornaliera", value=str(daily_pos), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="XP Settimanali", value=str(weekly_xp), inline=True)
    embed.add_field(name="Posizione Settimanale", value=str(weekly_pos), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="XP Mensili (Totale)", value=str(monthly_xp), inline=True)
    embed.add_field(name="Posizione Mensile", value=str(monthly_pos), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    if next_level_xp:
        embed.add_field(
            name=f"XP per prossimo livello ({next_level_role.name if next_level_role else 'Sconosciuto'})",
            value=f"{xp_to_next_level} XP mancanti",
            inline=False
        )
    else:
        embed.add_field(name="Livello massimo raggiunto", value="Hai raggiunto il livello più alto!", inline=False)

    embed.add_field(name="Ruoli attuali", value=", ".join(roles_have) if roles_have else "Nessuno", inline=False)
    embed.add_field(name="Ruoli prossimi da raggiungere", value=", ".join(roles_next) if roles_next else "Nessuno", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="classifica")
async def classifica(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, ctx.guild)
    await ctx.send(embed=embed)

# === COMANDI SOCIAL ===
@bot.command(name="twitch")
async def twitch(ctx):
    embed = discord.Embed(
        title="🎮 Twitch di Tw3nty Mars",
        description="[Clicca qui per visitare il canale Twitch](https://www.twitch.tv/tw3nty_mars?sr=a)",
        color=XP_COLOR
    )
    embed.set_thumbnail(url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png")
    await ctx.send(embed=embed)

@bot.command(name="youtube", aliases=["yt"])
async def youtube(ctx):
    embed = discord.Embed(
        title="▶️ Canale YouTube di Tw3nty Mars",
        description="[Guarda i video qui](https://www.youtube.com/channel/UC6E0F7DUBbF2ZP6GRV8cHFg)",
        color=XP_COLOR
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
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

@bot.command(name="instagram", aliases=["ig"])
async def instagram(ctx):
    embed = discord.Embed(
        title="📸 Instagram di Tw3nty Mars",
        description="[Visita il profilo Instagram](https://www.instagram.com/tw3nty_mars)",
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

@bot.command(name="discord", aliases=["ds"])
async def discord_cmd(ctx):
    embed = discord.Embed(
        title="💬 Server Discord",
        description="[Unisciti qui!](https://discord.gg/xKqWsTYRqy)",
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

# === COMANDI INFO ===
@bot.command(name="orari")
async def orari(ctx):
    embed = discord.Embed(
        title="📅 Streaming Schedule",
        description="TUTTI I GIORNI DALLE 18:00 ALLE 21:00🕑 (salvo imprevisti, vi avvisiamo su IG e DS)",
        color=XP_COLOR
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
            "!comandi - Questa lista\n"
            "!testxp - Aggiungi XP di test\n"
            "!setxp - Aggiungi XP personalizzati\n"
            "!rank - Vedi il tuo livello XP\n"
            "!classifica - Classifica mensile XP"
        ),
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

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
@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    scheduler.add_job(send_leaderboards, 'cron', day_of_week='mon', hour=8, minute=0, timezone=TIMEZONE)
    scheduler.start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)

