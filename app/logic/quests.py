"""
Hidden quest engine - surprise rewards based on behavior.

Users don't see these coming. That's the point.
Curiosity drives exploration, surprise drives dopamine.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, Task, UserTask, ActivityLog, Referral


# quest definitions: what triggers them and what you get
HIDDEN_QUESTS = {
    "first_referral": {
        "name": "First Blood",
        "description": "You made your first referral!",
        "points": 20,
        "condition": lambda stats: stats.get("referrals", 0) >= 1
    },
    "content_creator": {
        "name": "Voice of the Community",
        "description": "3 content submissions? You're on fire.",
        "points": 30,
        "condition": lambda stats: stats.get("content_count", 0) >= 3
    },
    "streak_master": {
        "name": "Consistency is Key",
        "description": "7-day streak! You're unstoppable.",
        "points": 50,
        "condition": lambda stats: stats.get("streak", 0) >= 7
    },
    "high_roller": {
        "name": "Points Millionaire",
        "description": "Hit 500 points. Baller status.",
        "points": 75,
        "condition": lambda stats: stats.get("points", 0) >= 500
    },
    "social_butterfly": {
        "name": "Social Butterfly",
        "description": "5 referrals? You know everybody.",
        "points": 40,
        "condition": lambda stats: stats.get("referrals", 0) >= 5
    }
}


async def check_hidden_quests(db: AsyncSession, user: User) -> list:
    """
    Check if user unlocked any hidden quests.
    Returns list of newly unlocked quests.
    """
    # gather user stats for condition checking
    stats = await _get_user_stats(db, user)

    # see which hidden quests they already completed
    result = await db.execute(
        select(UserTask.task_id).join(Task).where(
            UserTask.user_id == user.discord_id,
            Task.hidden == True,
            UserTask.status == "completed"
        )
    )
    completed_ids = set(result.scalars().all())

    # check all hidden quests
    newly_unlocked = []

    for quest_key, quest_def in HIDDEN_QUESTS.items():
        if quest_def["condition"](stats):
            # find or create the task
            task = await _get_or_create_hidden_task(db, quest_key, quest_def)

            if task.id not in completed_ids:
                # check if they already have this in progress
                existing = await db.execute(
                    select(UserTask).where(
                        UserTask.user_id == user.discord_id,
                        UserTask.task_id == task.id
                    )
                )
                if not existing.scalars().first():
                    # unlock it!
                    user_task = UserTask(
                        user_id=user.discord_id,
                        task_id=task.id,
                        status="completed",
                    )
                    db.add(user_task)

                    # give them the points
                    if not user.shadow_banned:
                        user.points += quest_def["points"]
                    else:
                        user.points += quest_def["points"] // 3  # shh

                    # log it
                    log = ActivityLog(
                        user_id=user.discord_id,
                        action="hidden_quest_unlocked",
                        metadata_={"quest": quest_key, "points": quest_def["points"]}
                    )
                    db.add(log)

                    newly_unlocked.append({
                        "key": quest_key,
                        "name": quest_def["name"],
                        "description": quest_def["description"],
                        "points": quest_def["points"]
                    })

    if newly_unlocked:
        await db.commit()

    return newly_unlocked


async def _get_user_stats(db: AsyncSession, user: User) -> dict:
    """Pull together all the stats we need for quest condition checks."""
    # referral count
    result = await db.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.discord_id)
    )
    referrals = result.scalar() or 0

    # content submissions
    result = await db.execute(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.user_id == user.discord_id,
            ActivityLog.action == "content_submitted"
        )
    )
    content_count = result.scalar() or 0

    return {
        "referrals": referrals,
        "content_count": content_count,
        "streak": user.streak,
        "points": user.points,
    }


async def _get_or_create_hidden_task(db: AsyncSession, key: str, definition: dict) -> Task:
    """Find a hidden task by name, or create it if it doesn't exist yet."""
    result = await db.execute(
        select(Task).where(Task.name == definition["name"], Task.hidden == True)
    )
    task = result.scalars().first()

    if not task:
        task = Task(
            name=definition["name"],
            description=definition["description"],
            points=definition["points"],
            type="hidden",
            hidden=True
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    return task
