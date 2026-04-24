"""
Referral engine - validates and scores referrals.

Quality > quantity. A referral that turns into an active user
is worth way more than 10 throwaway signups.
"""
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Referral, ActivityLog


async def validate_referral(db: AsyncSession, referrer_id: str, referred_user: str) -> dict:
    """
    Check if a referral is legit:
    - not referring yourself (c'mon)
    - not already referred
    - referrer actually exists
    """
    # no self-referrals
    if referrer_id == referred_user:
        return {"valid": False, "reason": "can't refer yourself"}

    # check if this person was already referred
    existing = await db.execute(
        select(Referral).where(Referral.referred_user == referred_user)
    )
    if existing.scalars().first():
        return {"valid": False, "reason": "already referred"}

    # make sure the referrer exists in our system
    referrer = await db.execute(
        select(User).where(User.discord_id == referrer_id)
    )
    if not referrer.scalars().first():
        return {"valid": False, "reason": "referrer not found"}

    return {"valid": True}


async def score_referral(referral: Referral, db: AsyncSession) -> float:
    """
    Score a referral based on quality signals.
    Higher score = better referral = more points.
    """
    score = 0.5  # baseline

    # check if the referred user became active
    referred = await db.execute(
        select(User).where(User.discord_id == referral.referred_user)
    )
    referred_user = referred.scalars().first()

    if referred_user:
        # active user? nice, bump the score
        if referred_user.last_active and referred_user.streak > 0:
            score += 0.2
        if referred_user.streak >= 7:
            score += 0.3  # they're hooked, great referral

    # check if referrer is spamming referrals (fraud signal)
    referrer = await db.execute(
        select(User).where(User.discord_id == referral.referrer_id)
    )
    referrer_user = referrer.scalars().first()

    if referrer_user and referrer_user.fraud_flag:
        score *= 0.5  # silently reduce score for flagged users

    return min(score, 1.0)


async def process_referral(db: AsyncSession, referrer_id: str, referred_user: str) -> dict:
    """Full referral pipeline - validate, create, score, reward."""
    validation = await validate_referral(db, referrer_id, referred_user)
    if not validation["valid"]:
        return {"success": False, **validation}

    # create the referral record
    referral = Referral(
        referrer_id=referrer_id,
        referred_user=referred_user,
        status="validated"
    )
    db.add(referral)

    # score it
    score = await score_referral(referral, db)
    referral.quality_score = score

    # points based on quality (10 base, up to 20 for great referrals)
    points_earned = int(10 * score) + 10

    # update referrer's points
    result = await db.execute(
        select(User).where(User.discord_id == referrer_id)
    )
    referrer = result.scalars().first()
    if referrer:
        if not referrer.shadow_banned:
            referrer.points += points_earned
        else:
            # they don't know, but they get less
            referrer.points += points_earned // 3

    # log it
    log = ActivityLog(
        user_id=referrer_id,
        action="referral_submitted",
        metadata_={"referred": referred_user, "score": score, "points": points_earned}
    )
    db.add(log)

    await db.commit()
    return {"success": True, "score": score, "points": points_earned}
