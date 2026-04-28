"""
Re-engagement engine - automated nudges to bring people back.

Nobody likes a dead community. We gently poke inactive users
with personalized messages to get them back in the game.
"""
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, ActivityLog


# when to trigger nudges
NUDGE_AFTER_DAYS = 3
AGGRESSIVE_NUDGE_AFTER_DAYS = 7

NUDGE_MESSAGES = {
    "gentle": [
        "Hey {name}! We miss you around here. Your streak is waiting! 🔥",
        "Psst {name}... there are new tasks available. Come check them out!",
        "{name}, you're close to the next rank! Don't lose momentum."
    ],
    "aggressive": [
        "{name}, your points are decaying! Get back in here before you lose your spot. ⚠️",
        "The leaderboard is moving without you, {name}. Time to make a comeback?",
        "{name} - 7 days without you. The community needs you back."
    ],
    "competitive": [
        "{name}, you're just {gap} points away from the top 10!",
        "Someone just passed you on the leaderboard, {name}. You gonna take that?"
    ]
}


async def get_inactive_users(db: AsyncSession) -> list:
    """Find users who need a nudge. Returns list of users + their nudge type."""
    today = datetime.date.today()

    result = await db.execute(
        select(User).where(User.last_active < today - datetime.timedelta(days=NUDGE_AFTER_DAYS))
    )
    inactive = result.scalars().all()

    nudges = []
    for user in inactive:
        days_away = (today - user.last_active).days if user.last_active else 999

        if days_away >= AGGRESSIVE_NUDGE_AFTER_DAYS:
            nudge_type = "aggressive"
        else:
            nudge_type = "gentle"

        # check if they'd be motivated by leaderboard proximity
        if user.points > 50:
            nudge_type = "competitive"

        nudges.append({
            "user_id": user.discord_id,
            "username": user.username,
            "days_inactive": days_away,
            "nudge_type": nudge_type,
            "points": user.points
        })

    return nudges


def get_nudge_message(nudge_type: str, username: str, gap: int = 0) -> str:
    """Pick a nudge message for the user."""
    import random
    messages = NUDGE_MESSAGES.get(nudge_type, NUDGE_MESSAGES["gentle"])
    msg = random.choice(messages)
    return msg.format(name=username, gap=gap)


async def process_reengagement(db: AsyncSession) -> dict:
    """
    Batch process re-engagement nudges.
    n8n calls this on a cron schedule.
    Returns stats about how many nudges were sent.
    """
    inactive = await get_inactive_users(db)
    nudges_sent = 0

    for user_info in inactive:
        # in a real setup, we'd DM the user via Discord
        # for now just log that we would have
        msg = get_nudge_message(user_info["nudge_type"], user_info["username"])

        log = ActivityLog(
            user_id=user_info["user_id"],
            action="reengagement_nudge",
            metadata_={
                "message": msg,
                "days_inactive": user_info["days_inactive"],
                "nudge_type": user_info["nudge_type"]
            }
        )
        db.add(log)
        nudges_sent += 1

    await db.commit()
    return {"nudges_sent": nudges_sent, "total_inactive": len(inactive)}
