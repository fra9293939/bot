import discord
from discord.ext import commands
import os
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

PRO_BOT_ID = 282859044593598464
CLASSIFICA_CHANNEL_ID = 1388623669886189628

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
        description="TUTTI I GIORNI DALLE 18:00 ALLE 21:00! 🕑\n(salvo imprevisti, vi avvisiamo su IG e Discord)",
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

    files = []
    if ctx.message.attachments:
        try:
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
        except Exception as e:
            await ctx.send(f"❌ Errore nel caricamento allegati: {e}")
            return

    # Cancellazione sicura del messaggio originale
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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Se il messaggio è inviato da Pro Bot e contiene /rank o /top
    if message.author.bot and message.author.id == PRO_BOT_ID:
        content_lower = message.content.lower()
        if "/rank" in content_lower or "/top" in content_lower:
            classifica_channel = bot.get_channel(CLASSIFICA_CHANNEL_ID)
            if classifica_channel:
                # Invia il messaggio nel canale classifica
                await classifica_channel.send(f"📊 Messaggio di {message.author.mention} spostato qui:\n{message.content}")
                # Prova a cancellare il messaggio originale
                try:
                    await message.delete()
                except discord.Forbidden:
                    print("❌ Non ho permessi per cancellare il messaggio di Pro Bot.")
                except Exception as e:
                    print(f"⚠️ Errore cancellando messaggio Pro Bot: {e}")
            return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")

keep_alive()

if not TOKEN:
    print("❌ Token non trovato! Imposta la variabile d'ambiente DISCORD_BOT_TOKEN.")
    exit(1)

bot.run(TOKEN)
