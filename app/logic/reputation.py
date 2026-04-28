"""
Reputation system - not all points are equal.

Content creation > referrals > participation.
Fraud signals tank your reputation.
High reputation = better rewards. Simple.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, ActivityLog, Referral

# how much each action type counts toward reputation
ACTION_WEIGHTS = {
    "content_submitted": 3.0,     # content is king
    "content_scored_high": 2.0,   # and good content is king of kings
    "referral_submitted": 1.5,    # solid but less than content
    "task_completed": 1.0,        # baseline
    "streak_updated": 0.5,        # consistency bonus
    "point_decay": -0.5,          # penalty
    "fraud_flagged": -5.0,        # big penalty
}

# reputation thresholds for reward tiers
TIERS = {
    "newcomer": (0, 20),
    "member": (20, 50),
    "veteran": (50, 100),
    "elite": (100, float('inf'))
}


async def calculate_reputation(db: AsyncSession, user: User) -> float:
    """
    Recalculate a user's reputation score based on their activity history.
    Call this periodically or after major actions.
    """
    # get all activity logs
    result = await db.execute(
        select(ActivityLog).where(ActivityLog.user_id == user.discord_id)
    )
    activities = result.scalars().all()

    score = 0.0
    for activity in activities:
        weight = ACTION_WEIGHTS.get(activity.action, 0.5)
        score += weight

    # streak bonus - consistency matters
    if user.streak >= 7:
        score += 10
    elif user.streak >= 3:
        score += 5

    # fraud penalty - if flagged, reputation takes a hit
    if user.fraud_flag:
        score *= 0.5
    if user.shadow_banned:
        score *= 0.3

    # update the user
    user.reputation_score = round(max(score, 0), 2)
    await db.commit()

    return user.reputation_score


def get_tier(reputation: float) -> str:
    """Get user's tier based on reputation score."""
    for tier, (low, high) in TIERS.items():
        if low <= reputation < high:
            return tier
    return "elite"


def get_reward_multiplier(reputation: float) -> float:
    """Higher reputation = better reward multiplier."""
    if reputation >= 100:
        return 1.5
    if reputation >= 50:
        return 1.25
    if reputation >= 20:
        return 1.1
    return 1.0
