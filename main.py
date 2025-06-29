import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo
from keep_alive import keep_alive  # Assicurati di avere questo file

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Configurazioni ---
CHANNEL_DAILY = 1388623669886189628
CHANNEL_WEEKLY = 1388623669886189628
CHANNEL_MONTHLY = 1388623669886189628
CHANNEL_LEVELUP = 1383429600016728074

XP_COLOR = 0xB500FF

ROLE_LEVELS = {
    0: 1383431607498571796,
    10: 1383433321630924922,
    20: 1383433334343860324,
    40: 1383433340715139244,
    60: 1383433337959481384,
    80: 1386849486948798535,
    100: 1383433343651020904,
}

TIMEZONE = ZoneInfo("Europe/Rome")
DATA_FILE = "xp_data.json"

# --- Variabili globali XP e reset ---
xp_daily = defaultdict(int)
xp_weekly = defaultdict(int)
xp_monthly = defaultdict(int)

last_daily_reset = None
last_weekly_reset = None
last_monthly_reset = None

# --- Funzioni salvataggio/caricamento JSON ---

def save_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    data = {
        "xp_daily": dict(xp_daily),
        "xp_weekly": dict(xp_weekly),
        "xp_monthly": dict(xp_monthly),
        "last_daily_reset": last_daily_reset.isoformat() if last_daily_reset else None,
        "last_weekly_reset": last_weekly_reset.isoformat() if last_weekly_reset else None,
        "last_monthly_reset": last_monthly_reset.isoformat() if last_monthly_reset else None,
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    global xp_daily, xp_weekly, xp_monthly
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    if not os.path.exists(DATA_FILE):
        now = datetime.now(TIMEZONE)
        last_daily_reset = now
        last_weekly_reset = now
        last_monthly_reset = now
        return

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    xp_daily = defaultdict(int, {int(k):v for k,v in data.get("xp_daily", {}).items()})
    xp_weekly = defaultdict(int, {int(k):v for k,v in data.get("xp_weekly", {}).items()})
    xp_monthly = defaultdict(int, {int(k):v for k,v in data.get("xp_monthly", {}).items()})

    last_daily_reset = datetime.fromisoformat(data["last_daily_reset"]) if data.get("last_daily_reset") else datetime.now(TIMEZONE)
    last_weekly_reset = datetime.fromisoformat(data["last_weekly_reset"]) if data.get("last_weekly_reset") else datetime.now(TIMEZONE)
    last_monthly_reset = datetime.fromisoformat(data["last_monthly_reset"]) if data.get("last_monthly_reset") else datetime.now(TIMEZONE)

# --- Reset XP ---

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

    save_data()

# --- Gestione XP ---

def add_xp(user_id, amount=10):
    xp_daily[user_id] += amount
    xp_weekly[user_id] += amount
    xp_monthly[user_id] += amount
    save_data()

async def update_roles(member, total_xp):
    guild = member.guild
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

# --- Eventi e comandi ---

@bot.event
async def on_ready():
    load_data()
    print(f"✅ Bot attivo come {bot.user}")
    send_leaderboards.start()

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.type == discord.ChannelType.private:
        return

    check_resets()
    add_xp(message.author.id)
    total_xp = xp_monthly[message.author.id]
    await update_roles(message.author, total_xp)

    await bot.process_commands(message)

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

# --- Comandi XP visibili a tutti ---

@bot.command(name="classifica")
async def classifica(ctx, periodo: str = "mensile"):
    periodo = periodo.lower()
    if periodo == "giornaliero" or periodo == "day":
        embed = create_leaderboard_embed("🏆 Classifica Giornaliera XP", xp_daily, ctx.guild)
    elif periodo == "settimanale" or periodo == "week":
        embed = create_leaderboard_embed("🏆 Classifica Settimanale XP", xp_weekly, ctx.guild)
    elif periodo == "mensile" or periodo == "month":
        embed = create_leaderboard_embed("🏆 Classifica Mensile XP", xp_monthly, ctx.guild)
    else:
        await ctx.send("Specifica il periodo: `giornaliero`, `settimanale` o `mensile`")
        return
    await ctx.send(embed=embed)

@bot.command(name="testxp")
async def test_xp(ctx):
    if not ctx.author.guild_permissions.manage_roles:
        await ctx.send("Non hai il permesso di usare questo comando.")
        return
    user_id = ctx.author.id
    add_xp(user_id, 100)
    total_xp = xp_monthly[user_id]
    await update_roles(ctx.author, total_xp)
    await ctx.send(f"🎉 {ctx.author.display_name}, ti ho aggiunto 100 XP e aggiornato i ruoli! XP totali mensili: {total_xp}")

# --- Comandi XP solo per MOD/ADMIN ---

@bot.group(name="xp", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def xp(ctx):
    await ctx.send("Usa i sottocomandi: `add`, `set`, `reset`")

@xp.command(name="add")
async def xp_add(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("L'importo deve essere positivo.")
        return
    add_xp(member.id, amount)
    total_xp = xp_monthly[member.id]
    await update_roles(member, total_xp)
    await ctx.send(f"Aggiunti {amount} XP a {member.display_name}. Totale mensile: {total_xp}")

@xp.command(name="set")
async def xp_set(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.send("L'importo non può essere negativo.")
        return
    xp_daily[member.id] = amount
    xp_weekly[member.id] = amount
    xp_monthly[member.id] = amount
    save_data()
    await update_roles(member, amount)
    await ctx.send(f"XP di {member.display_name} impostati a {amount}.")

@xp.command(name="reset")
async def xp_reset(ctx, member: discord.Member = None):
    if member:
        xp_daily.pop(member.id, None)
        xp_weekly.pop(member.id, None)
        xp_monthly.pop(member.id, None)
        await ctx.send(f"XP di {member.display_name} resettati.")
    else:
        xp_daily.clear()
        xp_weekly.clear()
        xp_monthly.clear()
        await ctx.send("XP di tutti resettati.")
    save_data()

@xp.error
async def xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Non hai i permessi per usare questo comando.")

# --- Comandi social e utility ---

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

@bot.command(name="orari")
async def orari(ctx):
    embed = discord.Embed(
        title="📅 Streaming Schedule",
        description="TUTTI I GIORNI DALLE 18:00 ALLE 21:00🕑 (salvo imprevisti, vi avvisiamo su ig e ds)",
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

@bot.command(name="comandi")
async def comandi(ctx):
    embed = discord.Embed(
        title="📜 Lista Comandi",
        description=(
            "**XP e Classifiche:**\n"
            "`!classifica [giornaliero|settimanale|mensile]` - Mostra la classifica XP (default mensile)\n"
            "\n"
            "**Social:**\n"
            "`!twitch` - Link Twitch\n"
            "`!youtube`/`!yt` - Link YouTube\n"
            "`!tiktok` - Link TikTok\n"
            "`!instagram`/`!ig` - Link Instagram\n"
            "`!discord`/`!ds` - Link Discord\n"
            "\n"
            "**Utility:**\n"
            "`!orari` - Orari streaming"
        ),
        color=XP_COLOR
    )
    await ctx.send(embed=embed)

# --- Avvio bot ---

keep_alive()
bot.run(TOKEN)
