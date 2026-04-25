"""
Streak system - tracks daily activity and builds habit loops.

3-day streak → bonus points
7-day streak → point multiplier
Streak break → reset to 0, tough luck
"""
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, ActivityLog


# streak reward thresholds
STREAK_BONUSES = {
    3: 15,   # 3 days → 15 bonus points
    7: 50,   # 7 days → 50 bonus points
    14: 100, # 2 weeks → 100 bonus points
    30: 250, # a whole month → 250 points
}

# multiplier when you hit 7+ streak
STREAK_MULTIPLIER = 1.5


async def update_streak(db: AsyncSession, user: User) -> dict:
    """Update streak when user does something. Call this on any activity."""
    today = datetime.date.today()

    if user.last_active is None:
        # first time ever
        user.streak = 1
        user.last_active = today
        await db.commit()
        return {"streak": 1, "bonus": 0, "multiplier": 1.0}

    days_since = (today - user.last_active).days

    if days_since == 0:
        # already active today, no change
        return {"streak": user.streak, "bonus": 0, "multiplier": get_multiplier(user.streak)}

    if days_since == 1:
        # consecutive day, nice
        user.streak += 1
        user.last_active = today
    else:
        # missed a day or more, streak broken
        user.streak = 1
        user.last_active = today

    # check if they earned a bonus
    bonus = STREAK_BONUSES.get(user.streak, 0)
    multiplier = get_multiplier(user.streak)

    if bonus > 0 and not user.shadow_banned:
        user.points += bonus

    # log the streak update
    log = ActivityLog(
        user_id=user.discord_id,
        action="streak_updated",
        metadata_={"streak": user.streak, "bonus": bonus}
    )
    db.add(log)
    await db.commit()

    return {"streak": user.streak, "bonus": bonus, "multiplier": multiplier}


def get_multiplier(streak: int) -> float:
    """Get point multiplier based on streak."""
    if streak >= 7:
        return STREAK_MULTIPLIER
    return 1.0


async def reset_streaks_daily(db: AsyncSession):
    """
    Cron job: find users who haven't been active today and break their streak.
    n8n calls this endpoint daily.
    """
    today = datetime.date.today()
    result = await db.execute(
        select(User).where(User.last_active < today - datetime.timedelta(days=1))
    )
    inactive_users = result.scalars().all()

    reset_count = 0
    for user in inactive_users:
        if user.streak > 0:
            user.streak = 0
            log = ActivityLog(
                user_id=user.discord_id,
                action="streak_broken",
                metadata_={"previous_streak": user.streak}
            )
            db.add(log)
            reset_count += 1

    await db.commit()
    return {"reset_count": reset_count}
