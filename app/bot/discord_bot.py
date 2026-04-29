"""
Discord bot - the user-facing interface for EngageX.

Users interact with the system entirely through Discord.
Slash commands for explicit actions.
"""
import discord
from discord.ext import commands
from app.database import async_session
from app.models import User, ActivityLog
from app.logic import (
    update_streak, check_hidden_quests,
    calculate_reputation, get_tier
)
from sqlalchemy import select, desc

# set up the bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --- helper ---

async def ensure_user(discord_id: str, username: str) -> User:
    """Make sure user exists in our DB. Create if they don't."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.discord_id == discord_id))
        user = result.scalars().first()
        if not user:
            user = User(discord_id=discord_id, username=username)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user


# --- slash commands ---

@bot.tree.command(name="points", description="Check your points and streak")
async def points_cmd(interaction: discord.Interaction):
    user = await ensure_user(str(interaction.user.id), interaction.user.name)
    tier = get_tier(user.reputation_score)
    await interaction.response.send_message(
        f"**{user.username}** — {user.points} pts | Streak: {user.streak} | Tier: {tier}"
    )


@bot.tree.command(name="leaderboard", description="See the top users")
async def leaderboard_cmd(interaction: discord.Interaction):
    async with async_session() as db:
        result = await db.execute(select(User).order_by(desc(User.points)).limit(10))
        users = result.scalars().all()

    if not users:
        await interaction.response.send_message("No one on the board yet. Be the first!")
        return

    lines = ["**Leaderboard**\n"]
    for i, u in enumerate(users):
        medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"`{i+1}.`")
        lines.append(f"{medal} **{u.username}** — {u.points} pts (streak {u.streak})")

    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="profile", description="Your full profile")
async def profile_cmd(interaction: discord.Interaction):
    user = await ensure_user(str(interaction.user.id), interaction.user.name)
    tier = get_tier(user.reputation_score)

    embed = discord.Embed(
        title=f"Profile: {user.username}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Points", value=str(user.points), inline=True)
    embed.add_field(name="Streak", value=f"{user.streak} days", inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)
    embed.add_field(name="Reputation", value=f"{user.reputation_score:.1f}", inline=True)
    embed.add_field(name="Last Active", value=str(user.last_active), inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="tasks", description="See available tasks")
async def tasks_cmd(interaction: discord.Interaction):
    async with async_session() as db:
        from app.models import Task, UserTask
        task_result = await db.execute(select(Task).where(Task.hidden == False))
        tasks = task_result.scalars().all()

        done_result = await db.execute(
            select(UserTask.task_id).where(
                UserTask.user_id == str(interaction.user.id),
                UserTask.status == "completed"
            )
        )
        done_ids = set(done_result.scalars().all())

    if not tasks:
        await interaction.response.send_message("No tasks available right now.")
        return

    lines = ["**Available Tasks**\n"]
    for t in tasks:
        status = "~~completed~~" if t.id in done_ids else f"**{t.points} pts**"
        lines.append(f"• {t.name} — {status}")

    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="referrals", description="See your referral stats")
async def referrals_cmd(interaction: discord.Interaction):
    async with async_session() as db:
        from app.models import Referral
        result = await db.execute(
            select(Referral).where(Referral.referrer_id == str(interaction.user.id))
        )
        refs = result.scalars().all()

    if not refs:
        await interaction.response.send_message("No referrals yet. Start sharing!")
        return

    validated = sum(1 for r in refs if r.status == "validated")
    avg_score = sum(r.quality_score for r in refs) / len(refs)

    await interaction.response.send_message(
        f"**Your Referrals** — Total: {len(refs)} | Validated: {validated} | Avg Quality: {avg_score:.1f}"
    )


# --- startup ---

async def setup_slash_commands():
    """Sync slash commands with Discord. Only needed once or when commands change."""
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
