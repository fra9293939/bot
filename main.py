import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timedelta
from collections import defaultdict

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Canali
CHANNEL_LEADERBOARD = 1388623669886189628  # canale classifica mensile
CHANNEL_LEVELUP = 1383429600016728074      # canale level-up

XP_COLOR = 0xB500FF

# XP in memoria
xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)

last_daily_reset = datetime.utcnow()
last_weekly_reset = datetime.utcnow()
last_monthly_reset = datetime.utcnow()

# Mappa livelli e ruoli (XP minimi : ruolo ID)
ROLE_LEVELS = {
    10: 1383433160749857196,   # livello 1
    100: 1383433321630924922,  # livello 10
    200: 1383433334343860324,  # livello 20
    400: 1383433340715139244,  # livello 40
    600: 1383433337959481384,  # livello 60
    800: 1386849486948798535,  # livello 80
    1000: 1383433343651020904, # livello 100
}

# Reset XP
def check_resets():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    now = datetime.utcnow()
    if (now - last_daily_reset) > timedelta(days=1):
        xp_daily.clear()
        last_daily_reset = now
    if now.isocalendar()[1] != last_weekly_reset.isocalendar()[1]:
        xp_weekly.clear()
        last_weekly_reset = now
    if now.month != last_monthly_reset.month:
        xp_monthly.clear()
        last_monthly_reset = now

# Aggiorna ruoli e manda messaggio solo se nuovo ruolo
async def update_roles_and_announce(member, total_xp):
    guild = member.guild
    eligible_levels = [(xp_req, role_id) for xp_req, role_id in ROLE_LEVELS.items() if total_xp >= xp_req]
    if not eligible_levels:
        return None

    max_xp_req, role_id_to_add = max(eligible_levels, key=lambda x: x[0])
    role_to_add = guild.get_role(role_id_to_add)
    if not role_to_add:
        return None

    if role_to_add in member.roles:
        return None  # Ha già il ruolo, niente da fare

    try:
        # NON rimuovere i ruoli più bassi
        await member.add_roles(role_to_add, reason="Aggiornamento ruolo per XP")

        # Manda embed nel canale level-up
        channel = guild.get_channel(CHANNEL_LEVELUP)
        if channel:
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Congratulazioni {member.mention}, hai raggiunto il ruolo **{role_to_add.name}**!",
                color=XP_COLOR
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"XP raggiunti: {total_xp}")
            await channel.send(embed=embed)

        print(f"Ruolo {role_to_add.name} assegnato a {member.display_name}")
        return role_to_add.name
    except Exception as e:
        print(f"Errore assegnazione ruoli a {member.display_name}: {e}")
        return None

# Aggiungi XP 10 per messaggio
def add_xp(user_id):
    xp_daily[user_id] += 10
    xp_weekly[user_id] += 10
    xp_monthly[user_id] += 10

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.type == discord.ChannelType.private:
        return

    check_resets()
    add_xp(message.author.id)

    total_xp = xp_monthly[message.author.id]
    member = message.author
    await update_roles_and_announce(member, total_xp)

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
        ch_leaderboard = guild.get_channel(CHANNEL_LEADERBOARD)
        if not ch_leaderboard:
            print(f"Canale leaderboard non trovato nel server {guild.name}")
            continue
        try:
            await ch_leaderboard.send(embed=create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, guild))
        except Exception as e:
            print(f"Errore invio classifica in {guild.name}: {e}")

# --- Comandi social ---

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
        description="TUTTI I GIORNI DALLE 18:00 ALLE 21:00🕑 (salvo imprevisti, vi avvisiamo su ig e ds)",
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

@bot.command(name="send")
async def send(ctx, *, message=None):
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Non hai i permessi per usare questo comando.")
        return

