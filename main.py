import discord
from discord.ext import commands, tasks
import os
import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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

DATA_FILE = "xp_data.json"
MSG_ID_FILE = "leaderboard_msg_ids.json"
COOLDOWN_FILE = "cooldowns.json"

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

leaderboard_messages = {"daily": None, "weekly": None, "monthly": None, "top": None}

# --- XP LOGIC ---
def xp_to_level(xp):
    return int((xp / 50) ** (1/3))

def xp_for_next_level(level):
    return 50 * (level + 1) ** 3

def xp_to_next_level(xp):
    level = xp_to_level(xp)
    next_xp = xp_for_next_level(level)
    return next_xp - xp

def get_next_role(level):
    sorted_levels = sorted(ROLE_LEVELS.keys())
    for l in sorted_levels:
        if l > level:
            return l, ROLE_LEVELS[l]
    return None, None

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
async def check_level_up(user_id, member, level):
    channel = bot.get_channel(CHANNEL_LEVELUP)
    if channel:
        embed = discord.Embed(
            description=f"🎉 {member.mention} è salito al livello **{level}**!",
            color=XP_COLOR
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)

    # Ruolo sbloccato
    for lvl, role_id in sorted(ROLE_LEVELS.items(), reverse=True):
        if level >= lvl:
            role = member.guild.get_role(role_id)
            if role and role not in member.roles:
                await member.add_roles(role)
                if channel:
                    embed = discord.Embed(
                        description=f"🔓 {member.mention} ha sbloccato il ruolo per il **livello {lvl}**!",
                        color=XP_COLOR
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    await channel.send(embed=embed)
            break

def save_data():
    data = {
        "xp_daily": dict(xp_daily),
        "xp_weekly": dict(xp_weekly),
        "xp_monthly": dict(xp_monthly),
        "user_total_xp": dict(user_total_xp),
        "last_daily_reset": last_daily_reset.isoformat() if last_daily_reset else None,
        "last_weekly_reset": last_weekly_reset.isoformat() if last_weekly_reset else None,
        "last_monthly_reset": last_monthly_reset.isoformat() if last_monthly_reset else None
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def load_data():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    if not os.path.exists(DATA_FILE):
        now = datetime.now(TIMEZONE)
        last_daily_reset = now
        last_weekly_reset = now
        last_monthly_reset = now
        return
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    for k in data.get("xp_daily", {}):
        xp_daily[int(k)] = data["xp_daily"][k]
    for k in data.get("xp_weekly", {}):
        xp_weekly[int(k)] = data["xp_weekly"][k]
    for k in data.get("xp_monthly", {}):
        xp_monthly[int(k)] = data["xp_monthly"][k]
    for k in data.get("user_total_xp", {}):
        user_total_xp[int(k)] = data["user_total_xp"][k]
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

def get_position(user_id, ranking_dict):
    sorted_list = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(sorted_list, 1):
        if uid == user_id:
            return i
    return None

def get_user_roles(member):
    roles = [role.name for role in member.roles if role.id in ROLE_LEVELS.values()]
    return roles if roles else ["Nessun ruolo"]

# --- LEADERBOARD EMBEDS ---

def create_leaderboard_embed(title, ranking_dict):
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

# --- COMMANDS ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    if can_get_xp(user_id):
        old_level = xp_to_level(user_total_xp[user_id])  # livello prima del guadagno
        gained = random.randint(10, 20)
        add_xp(user_id, gained)
        save_data()
        new_level = xp_to_level(user_total_xp[user_id])  # livello dopo

        if new_level > old_level:
            await check_level_up(user_id, message.author, new_level)

    await bot.process_commands(message)


# Comando !rank

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
    next_role_name = None
    if next_role_id:
        next_role = ctx.guild.get_role(next_role_id)
        if next_role:
            next_role_name = f"{next_role.name} (Lv {next_role_level})"
    else:
        next_role_name = "Nessun ruolo successivo"

    roles_names = get_user_roles(member)

    embed = discord.Embed(title=f"📊 Rank di {member.display_name}", color=XP_COLOR)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Livello", value=str(level), inline=True)
    embed.add_field(name="XP Totali", value=str(xp), inline=True)
    embed.add_field(name="XP per prossimo livello", value=str(xp_needed), inline=True)
    embed.add_field(name="Prossimo ruolo", value=next_role_name, inline=False)
    embed.add_field(name="Ruoli attuali", value=", ".join(roles_names), inline=False)
    embed.add_field(name="Posizione Global", value=str(global_pos), inline=True)
    embed.add_field(name="Posizione Giornaliera", value=str(daily_pos), inline=True)
    embed.add_field(name="Posizione Settimanale", value=str(weekly_pos), inline=True)
    embed.add_field(name="Posizione Mensile", value=str(monthly_pos), inline=True)

    await ctx.send(embed=embed)

# Comandi top/day/week/month

@bot.command(name="top")
async def top_command(ctx):
    embed = create_leaderboard_embed("🏆 Classifica Globale Top 10", user_total_xp)
    await ctx.send(embed=embed)

@bot.command()
async def day(ctx):
    embed = create_leaderboard_embed("📅 Classifica Giornaliera Top 10", xp_daily)
    await ctx.send(embed=embed)

@bot.command()
async def week(ctx):
    embed = create_leaderboard_embed("📅 Classifica Settimanale Top 10", xp_weekly)
    await ctx.send(embed=embed)

@bot.command()
async def month(ctx):
    embed = create_leaderboard_embed("📅 Classifica Mensile Top 10", xp_monthly)
    await ctx.send(embed=embed)

# Comando comandi (senza addxp e resetxp)

@bot.command()
async def comandi(ctx):
    cmds = [
        "!rank [@utente] — Mostra il rank dettagliato di un utente",
        "!top — Classifica globale",
        "!day — Classifica giornaliera",
        "!week — Classifica settimanale",
        "!month — Classifica mensile",
        "!orari — Mostra gli orari del bot e link social:\n"
        "• Discord: /ds — https://discord.gg/7xSGy3VQr3\n"
        "• YouTube: /yt — https://www.youtube.com/@tw3ntymars\n"
        "• Instagram: /ig — https://www.instagram.com/tw3nty.mars/\n"
        "• Twitch: /twitch — https://www.twitch.tv/tw3ntymars\n"
        "• TikTok: /tiktok — https://www.tiktok.com/@tw3nty.mars"
    ]

    txt = "**Comandi disponibili:**\n" + "\n".join(cmds)

    embed = discord.Embed(
        title="Lista Comandi",
        description=txt,
        color=0xB500FF  # viola
    )
    await ctx.send(embed=embed)



# Comando orari (link social)

@bot.command()
async def orari(ctx):
    txt = "**Link Social:**\n"
    for k,v in SOCIAL_LINKS.items():
        txt += f"{k.capitalize()}: {v}\n"
    await ctx.send(txt)

# Comandi admin (addxp e resetxp) nascosti da !comandi

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command(name="addxp")
@is_admin()
async def addxp(ctx, member: discord.Member, amount: int):
    add_xp(member.id, amount)
    save_data()
    await ctx.send(f"Aggiunti {amount} XP a {member.display_name}")

@bot.command(name="resetxp")
@is_admin()
async def resetxp(ctx, member: discord.Member = None):
    if member:
        user_total_xp[member.id] = 0
        xp_daily[member.id] = 0
        xp_weekly[member.id] = 0
        xp_monthly[member.id] = 0
        await ctx.send(f"XP resettati per {member.display_name}")
    else:
        user_total_xp.clear()
        xp_daily.clear()
        xp_weekly.clear()
        xp_monthly.clear()
        await ctx.send("XP resettati per tutti")
    save_data()
@bot.command()
@is_admin()
async def setlevel(ctx, member: discord.Member, level: int):
    if level < 0:
        await ctx.send("Il livello deve essere 0 o superiore.")
        return
    xp = 50 * (level ** 3)
    user_total_xp[member.id] = xp
    xp_daily[member.id] = 0
    xp_weekly[member.id] = 0
    xp_monthly[member.id] = 0
    save_data()
    await ctx.send(f"L'XP di {member.display_name} è stata impostata per livello {level} ({xp} XP).")

# --- LEADERBOARD AUTOMATIC UPDATE ---

@tasks.loop(minutes=5)
async def leaderboard_update():
    try:
        guild = bot.guilds[0]  # assumo un solo server, o cambia con ID specifico
        channels = {
            "daily": bot.get_channel(CHANNEL_DAILY),
            "weekly": bot.get_channel(CHANNEL_WEEKLY),
            "monthly": bot.get_channel(CHANNEL_MONTHLY),
            "top": bot.get_channel(CHANNEL_DAILY),  # puoi cambiare canale per top globale se vuoi
        }
        for key, channel in channels.items():
            if channel is None:
                continue
            embed = None
            if key == "daily":
                embed = create_leaderboard_embed("📅 Classifica Giornaliera Top 10", xp_daily)
            elif key == "weekly":
                embed = create_leaderboard_embed("📅 Classifica Settimanale Top 10", xp_weekly)
            elif key == "monthly":
                embed = create_leaderboard_embed("📅 Classifica Mensile Top 10", xp_monthly)
            elif key == "top":
                embed = create_leaderboard_embed("🏆 Classifica Globale Top 10", user_total_xp)

            # invio o aggiorno messaggio
            msg_id = leaderboard_messages.get(key)
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                except:
                    sent = await channel.send(embed=embed)
                    leaderboard_messages[key] = sent.id
            else:
                sent = await channel.send(embed=embed)
                leaderboard_messages[key] = sent.id
    except Exception as e:
        print(f"Errore leaderboard update: {e}")

# --- RESET SCHEDULE (esempio semplice, va migliorato) ---

@tasks.loop(minutes=60)
async def reset_check():
    global last_daily_reset, last_weekly_reset, last_monthly_reset
    now = datetime.now(TIMEZONE)

    # reset giornaliero a mezzanotte
    if last_daily_reset.date() < now.date():
        reset_daily()
        save_data()

    # reset settimanale lunedì
    if last_weekly_reset.isocalendar()[1] < now.isocalendar()[1]:
        reset_weekly()
        save_data()

    # reset mensile primo giorno mese
    if last_monthly_reset.month < now.month:
        reset_monthly()
        save_data()

@bot.event
async def on_ready():
    print(f"Bot pronto come {bot.user}")
    load_data()
    leaderboard_update.start()
    reset_check.start()

keep_alive()
bot.run(TOKEN)
