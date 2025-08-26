import discord
from discord.ext import commands
from discord import ui
import asyncio
import os
from keep_alive import keep_alive

# --- Config ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Eventi ---
@bot.event
async def on_ready():
    print(f"✅ Bot attivo come {bot.user}")

# --- Comando embed universale ---
@bot.command(name="embed")
async def embed_cmd(ctx, colore: str = None, *, contenuto: str):
    if colore:
        colore = colore.lstrip("#")
        try:
            colore_int = int(colore, 16)
        except ValueError:
            await ctx.send("❌ Colore non valido! Usa esadecimale tipo #FF0000")
            return
    else:
        colore_int = discord.Color.blue().value

    blocchi = contenuto.split(";;")

    # Primo blocco come titolo
    titolo = blocchi[0].strip() if blocchi else "Embed"

    # Il resto diventa descrizione
    descrizione = ""
    for blocco in blocchi[1:]:
        if "||" in blocco:
            rosso, bianco = map(str.strip, blocco.split("||", 1))
            descrizione += f"```diff\n- {rosso}\n```\n{bianco}\n\n"
        else:
            descrizione += f"{blocco.strip()}\n\n"

    embed = discord.Embed(title=titolo, description=descrizione.strip(), color=colore_int)
    message = await ctx.send(embed=embed)

    bot.last_embed = message
    bot.last_embed_author = ctx.author

# --- Comando modifica embed ---
@bot.command(name="modificaembed")
async def modificaembed(ctx, *, nuovo_contenuto: str):
    if not hasattr(bot, "last_embed"):
        await ctx.send("⚠️ Non ci sono embed da modificare!")
        return

    if ctx.author != bot.last_embed_author and not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Non hai i permessi per modificare questo embed.")
        return

    blocchi = nuovo_contenuto.split(";;")
    titolo = blocchi[0].strip() if blocchi else "Embed"

    descrizione = ""
    for blocco in blocchi[1:]:
        if "||" in blocco:
            rosso, bianco = map(str.strip, blocco.split("||", 1))
            descrizione += f"```diff\n- {rosso}\n```\n{bianco}\n\n"
        else:
            descrizione += f"{blocco.strip()}\n\n"

    nuovo_embed = discord.Embed(title=titolo, description=descrizione.strip(), color=bot.last_embed.embeds[0].color.value)
    await bot.last_embed.edit(embed=nuovo_embed)

    await ctx.send("✅ Embed aggiornato!")


# --- Avvio bot con retry ---
async def start_bot():
    while True:
        try:
            keep_alive()
            await bot.start(TOKEN)
        except discord.HTTPException as e:
            if e.status == 429:
                print("⚠️ Rate limit rilevato! Aspetto 15 minuti prima di riprovare...")
                await asyncio.sleep(900)
            else:
                print(f"Errore HTTP: {e}")
                await asyncio.sleep(60)
        except Exception as e:
            print(f"Errore generico: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(start_bot())

