import os
import re
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from link_manager import create_code, consume_code, get_link, unlink

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


def embed(title, desc, color=discord.Color.blue()):
    return discord.Embed(title=title, description=desc, color=color)


# ---------------- LINK COMMANDS ----------------

@bot.tree.command(name="linkcode")
async def linkcode(interaction: discord.Interaction, username: str, uuid: str | None = None):
    await interaction.response.defer(ephemeral=True)

    result = create_code(username, uuid or "")

    if result["ok"]:
        await interaction.followup.send(
            embed=embed(
                "Code Generated",
                f"Code: `{result['code']}`\nExpires: <t:{result['expires_at']}:R>",
                discord.Color.green()
            ),
            ephemeral=True
        )
    else:
        await interaction.followup.send(embed=embed("Error", result["error"], discord.Color.red()), ephemeral=True)


@bot.tree.command(name="linkmc")
async def linkmc(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)

    result = consume_code(
        code.upper().strip(),
        str(interaction.user.id),
        str(interaction.user)
    )

    if result["ok"]:
        await interaction.followup.send(
            embed=embed("Linked", f"Linked to `{result['link']['minecraft_name']}`", discord.Color.green()),
            ephemeral=True
        )
    else:
        await interaction.followup.send(embed=embed("Error", result["error"], discord.Color.red()), ephemeral=True)


@bot.tree.command(name="mcaccount")
async def mcaccount(interaction: discord.Interaction):
    entry = get_link(str(interaction.user.id))

    if not entry:
        await interaction.response.send_message(embed=embed("None", "No linked account"), ephemeral=True)
        return

    await interaction.response.send_message(
        embed=embed(
            "Linked Account",
            f"Name: `{entry['minecraft_name']}`\nUUID: `{entry['minecraft_uuid']}`"
        ),
        ephemeral=True
    )


@bot.tree.command(name="unlinkmc")
async def unlinkmc(interaction: discord.Interaction):
    removed = unlink(str(interaction.user.id))

    if not removed:
        await interaction.response.send_message(embed=embed("Error", "Not linked"), ephemeral=True)
        return

    await interaction.response.send_message(embed=embed("Unlinked", "Account removed", discord.Color.orange()), ephemeral=True)


# ---------------- READY ----------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()


def run_bot():
    bot.run(TOKEN)
