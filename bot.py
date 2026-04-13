import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from link_manager import (
    create_code,
    consume_code,
    get_link,
    load_role_rank_sync,
    unlink,
    update_linked_player_ranks,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def embed(title, desc, color=discord.Color.blue()):
    return discord.Embed(title=title, description=desc, color=color)


def resolve_ftb_ranks_for_member(member: discord.Member) -> list[str]:
    role_to_rank = load_role_rank_sync()
    ranks = []

    for role in member.roles:
        mapped = role_to_rank.get(str(role.id))
        if mapped:
            ranks.append(mapped)

    return sorted(set(ranks))


async def sync_member_ranks(member: discord.Member):
    link = get_link(str(member.id))
    if not link:
        return None

    ranks = resolve_ftb_ranks_for_member(member)
    return update_linked_player_ranks(str(member.id), ranks)


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
                discord.Color.green(),
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            embed=embed("Error", result["error"], discord.Color.red()), ephemeral=True
        )


@bot.tree.command(name="linkmc")
async def linkmc(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)

    result = consume_code(code.upper().strip(), str(interaction.user.id), str(interaction.user))

    if result["ok"]:
        if isinstance(interaction.user, discord.Member):
            synced = await sync_member_ranks(interaction.user)
            ranks_text = ", ".join(synced.get("ftb_ranks", [])) if synced else "none"
        else:
            ranks_text = "none"

        await interaction.followup.send(
            embed=embed(
                "Linked",
                f"Linked to `{result['link']['minecraft_name']}`\nFTB ranks queued: `{ranks_text}`",
                discord.Color.green(),
            ),
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            embed=embed("Error", result["error"], discord.Color.red()), ephemeral=True
        )


@bot.tree.command(name="mcaccount")
async def mcaccount(interaction: discord.Interaction):
    entry = get_link(str(interaction.user.id))

    if not entry:
        await interaction.response.send_message(
            embed=embed("None", "No linked account"), ephemeral=True
        )
        return

    ranks = ", ".join(entry.get("ftb_ranks", [])) or "none"

    await interaction.response.send_message(
        embed=embed(
            "Linked Account",
            f"Name: `{entry['minecraft_name']}`\nUUID: `{entry['minecraft_uuid']}`\nFTB ranks: `{ranks}`",
        ),
        ephemeral=True,
    )


@bot.tree.command(name="unlinkmc")
async def unlinkmc(interaction: discord.Interaction):
    removed = unlink(str(interaction.user.id))

    if not removed:
        await interaction.response.send_message(
            embed=embed("Error", "Not linked"), ephemeral=True
        )
        return

    await interaction.response.send_message(
        embed=embed("Unlinked", "Account removed", discord.Color.orange()), ephemeral=True
    )


@bot.tree.command(name="syncmcranks")
async def syncmcranks(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            embed=embed("Error", "Guild-only command", discord.Color.red()), ephemeral=True
        )
        return

    synced = await sync_member_ranks(interaction.user)
    if not synced:
        await interaction.response.send_message(
            embed=embed("Info", "No linked account found"), ephemeral=True
        )
        return

    ranks = ", ".join(synced.get("ftb_ranks", [])) or "none"
    await interaction.response.send_message(
        embed=embed("Synced", f"FTB ranks now: `{ranks}`", discord.Color.green()),
        ephemeral=True,
    )


# ---------------- EVENTS ----------------

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    before_roles = {r.id for r in before.roles}
    after_roles = {r.id for r in after.roles}

    if before_roles != after_roles:
        await sync_member_ranks(after)


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
