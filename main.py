import discord
from discord.ext import commands
import os
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # per accedere ai membri
bot = commands.Bot(command_prefix="!", intents=intents)

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
            "!comandi - Questa lista\n"
            "!topmessaggi - Classifica messaggi top 10"
        ),
        color=0xB500FF
    )
    await ctx.send(embed=embed)

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
            await ctx.send(f"❌ Errore nel caricamento allegati: {e}")
            return

    try:
        await ctx.message.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        await ctx.send("❌ Non ho i permessi per eliminare il messaggio.")
    except Exception as e:
        await ctx.send(f"⚠️ Errore durante l'eliminazione del messaggio: {e}")

    if message or files:
        await ctx.send(content=message, files=files)
    else:
        await ctx.send("⚠️ Nessun messaggio o allegato da inviare.")

# --- Comando top messaggi ---

@bot.command(name="topmessaggi")
async def topmessaggi(ctx):
    target_channel_id = 1388623669886189628
    target_channel = bot.get_channel(target_channel_id)
    if target_channel is None:
        await ctx.send("❌ Canale per la classifica non trovato!")
        return

    counts = {}
    try:
        async for message in ctx.channel.history(limit=1000):
            if message.author.bot:
                continue
            counts[message.author.id] = counts.get(message.author.id, 0) + 1
    except discord.Forbidden:
        await ctx.send("❌ Non ho i permessi per leggere la cronologia di questo canale.")
        return

    top10 = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Classifica Top 10 Messaggi (ultimi 1000 messaggi canale)",
        color=0xB500FF,
    )
    for i, (user_id, msg_count) in enumerate(top10, start=1):
        member = ctx.guild.get_member(user_id)
        if member:
            embed.add_field(name=f"#{i} - {member.display_name}", value=f"Messaggi: {msg_count}", inline=False)
        else:
            embed.add_field(name=f"#{i} - Utente sconosciuto", value=f"Messaggi: {msg_count}", inline=False)

    await target_channel.send(embed=embed)
    await ctx.message.add_reaction("✅")

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")
    await bot.wait_until_ready()

keep_alive()
bot.run(TOKEN)
