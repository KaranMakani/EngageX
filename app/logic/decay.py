"""
Point decay - inactive users slowly lose points and leaderboard position.

Keeps things competitive. You can't just score big once and coast forever.
"""
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, ActivityLog

# lose 2% of points per day of inactivity
DECAY_RATE = 0.02
# minimum points (don't go negative)
MIN_POINTS = 0
# days before decay kicks in
GRACE_PERIOD_DAYS = 3


async def apply_decay(db: AsyncSession) -> dict:
    """
    Daily cron job: decay points for inactive users.
    n8n calls this endpoint once a day.
    """
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=GRACE_PERIOD_DAYS)

    # find users who've been inactive past the grace period
    result = await db.execute(
        select(User).where(
            User.last_active < cutoff,
            User.points > MIN_POINTS
        )
    )
    inactive_users = result.scalars().all()

    decayed_count = 0
    total_decayed = 0

    for user in inactive_users:
        days_inactive = (today - user.last_active).days
        # compound decay: more days = more loss
        decay_factor = (1 - DECAY_RATE) ** days_inactive
        original_points = user.points
        user.points = max(int(user.points * decay_factor), MIN_POINTS)

        lost = original_points - user.points
        if lost > 0:
            decayed_count += 1
            total_decayed += lost

            log = ActivityLog(
                user_id=user.discord_id,
                action="point_decay",
                metadata_={"lost": lost, "days_inactive": days_inactive, "remaining": user.points}
            )
            db.add(log)

    await db.commit()
    return {"decayed_users": decayed_count, "total_points_lost": total_decayed}
