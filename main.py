import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PRO_BOT_ID = 282859044593598464
TARGET_CHANNEL_ID = 1388623669886189628

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")

import aiohttp
from io import BytesIO

# --- COMANDI DEL BOT ---
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
        description="TUTTI I GIORNI DALLE 20:45 ALLE 23:45🕑 (salvo imprevisti, vi avvisiamo su ig e ds)",
        color=0xB500FF
    )
    await ctx.send(embed=embed)
    
@bot.command(name="socials")
async def socials(ctx):
    embed = discord.Embed(
        title="🌐 Tutti i Social di Tw3nty Mars",
        description="[Clicca qui per accedere a tutti i link](https://linktr.ee/Tw3ntyMars)",
        color=0xB500FF
    )
    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Linktree_Logo.svg/512px-Linktree_Logo.svg.png")
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
            "!socials - Tutti i link social\n"
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
        
@bot.command(name="embeddiff")
async def embeddiff(ctx, red_text: str, *, description: str = ""):
    """
    Manda un embed con una parte rossa (diff) e una descrizione sotto.
    Uso: !embeddiff "DISCORD TOS" Si prega di rispettare i termini...
    """
    embed = discord.Embed(
        description=(
            f"```diff\n- {red_text}\n```\n"
            f"{description}"
        ),
        color=0xB500FF
    )
    await ctx.send(embed=embed)




# --- Gestione connessione con retry e pausa se 429 ---
async def start_bot():
    while True:
        try:
            keep_alive()
            await bot.start(TOKEN)
        except discord.HTTPException as e:
            if e.status == 429:
                print("⚠️ Rate limit rilevato! Aspetto 15 minuti prima di riprovare...")
                await asyncio.sleep(900)  # 15 minuti
            else:
                print(f"Errore HTTP: {e}")
                await asyncio.sleep(60)  # Attende 1 minuto prima di riprovare
        except Exception as e:
            print(f"Errore generico: {e}")
            await asyncio.sleep(60)  # Attende 1 minuto prima di riprovare

if __name__ == "__main__":
    asyncio.run(start_bot())

