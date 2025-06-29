import discord
from discord.ext import commands
import os
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

@bot.event
async def on_message(message):
    # Ignora i messaggi dal bot stesso
    if message.author.id == bot.user.id:
        return

    # Debug: stampa messaggi di Pro Bot per capire struttura
    if message.author.id == PRO_BOT_ID:
        print(f"Messaggio Pro Bot ricevuto. Content: '{message.content}' - Embeds: {len(message.embeds)}")

        content_lower = message.content.lower() if message.content else ""

        # Caso testo semplice
        if content_lower.startswith("/rank") or content_lower.startswith("/top"):
            try:
                await message.delete()
                target_channel = bot.get_channel(TARGET_CHANNEL_ID) or await bot.fetch_channel(TARGET_CHANNEL_ID)
                forward_content = f"Messaggio spostato dal canale #{message.channel.name}:\n{message.content}"
                await target_channel.send(forward_content)
            except Exception as e:
                print(f"Errore nello spostare messaggio Pro Bot (testo): {e}")
        
        # Caso embed (ad esempio comandi slash che rispondono con embed)
        else:
            for embed in message.embeds:
                title = embed.title.lower() if embed.title else ""
                description = embed.description.lower() if embed.description else ""
                if ("rank" in title or "top" in title) or ("rank" in description or "top" in description):
                    try:
                        await message.delete()
                        target_channel = bot.get_channel(TARGET_CHANNEL_ID) or await bot.fetch_channel(TARGET_CHANNEL_ID)
                        forward_content = (
                            f"Messaggio spostato dal canale #{message.channel.name}:\n"
                            f"Embed Title: {embed.title}\n"
                            f"Embed Description: {embed.description}"
                        )
                        await target_channel.send(forward_content)
                    except Exception as e:
                        print(f"Errore nello spostare messaggio Pro Bot (embed): {e}")
                    break

    # Permetti ai comandi di funzionare normalmente
    await bot.process_commands(message)

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
            "!send - Invia messaggi o allegati (permessi richiesti)"
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

keep_alive()
bot.run(TOKEN)

