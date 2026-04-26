"""
Fraud detection - catches sus behavior silently.

The key here is stealth. We never tell users they're flagged.
We just quietly reduce their rewards and keep an eye on them.
No drama, no public callouts.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, Referral, ActivityLog
import datetime


# thresholds that trigger fraud detection
MAX_REFERRALS_PER_DAY = 5
MAX_REFERRALS_PER_HOUR = 3
MIN_ACTIVITY_GAP_SECONDS = 10  # actions faster than this are sus


async def detect_fraud(db: AsyncSession, user_id: str) -> dict:
    """
    Run fraud checks on a user. Returns risk assessment.
    Called by n8n workflow or before rewarding.
    """
    result = await db.execute(
        select(User).where(User.discord_id == user_id)
    )
    user = result.scalars().first()
    if not user:
        return {"risk": "unknown", "flags": []}

    flags = []

    # check 1: too many referrals in a short time
    referral_flags = await _check_referral_spam(db, user_id)
    flags.extend(referral_flags)

    # check 2: identical activity patterns (bot behavior)
    pattern_flags = await _check_activity_patterns(db, user_id)
    flags.extend(pattern_flags)

    # check 3: low-quality content spam
    spam_flags = await _check_content_spam(db, user_id)
    flags.extend(spam_flags)

    # calculate risk level
    risk = _calculate_risk(flags)

    # silently update user status
    if risk in ("high", "critical"):
        user.fraud_flag = True
    if risk == "critical":
        user.shadow_banned = True
    elif risk == "low" and user.fraud_flag:
        # they've been good, maybe unflag them
        user.fraud_flag = False
        user.shadow_banned = False

    await db.commit()

    return {"risk": risk, "flags": flags}


async def _check_referral_spam(db: AsyncSession, user_id: str) -> list:
    """Check if someone's spamming referrals."""
    flags = []
    now = datetime.datetime.utcnow()

    # referrals today
    today_start = now.replace(hour=0, minute=0, second=0)
    result = await db.execute(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user_id,
            Referral.created_at >= today_start
        )
    )
    today_count = result.scalar() or 0

    if today_count >= MAX_REFERRALS_PER_DAY:
        flags.append({
            "type": "referral_spam_daily",
            "detail": f"{today_count} referrals today (max {MAX_REFERRALS_PER_DAY})"
        })

    # referrals in the last hour
    hour_ago = now - datetime.timedelta(hours=1)
    result = await db.execute(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user_id,
            Referral.created_at >= hour_ago
        )
    )
    hour_count = result.scalar() or 0

    if hour_count >= MAX_REFERRALS_PER_HOUR:
        flags.append({
            "type": "referral_spam_hourly",
            "detail": f"{hour_count} referrals in last hour (max {MAX_REFERRALS_PER_HOUR})"
        })

    return flags


async def _check_activity_patterns(db: AsyncSession, user_id: str) -> list:
    """Look for bot-like activity patterns - too regular, too fast."""
    flags = []

    # get recent activity
    result = await db.execute(
        select(ActivityLog).where(
            ActivityLog.user_id == user_id,
        ).order_by(ActivityLog.created_at.desc()).limit(20)
    )
    activities = result.scalars().all()

    if len(activities) < 3:
        return flags

    # check for suspiciously regular timing
    gaps = []
    for i in range(len(activities) - 1):
        gap = (activities[i].created_at - activities[i+1].created_at).total_seconds()
        gaps.append(gap)

    if gaps:
        # if all gaps are nearly identical, that's bot behavior
        avg_gap = sum(gaps) / len(gaps)
        all_similar = all(abs(g - avg_gap) < 2 for g in gaps)
        if all_similar and avg_gap < 60:
            flags.append({
                "type": "bot_pattern",
                "detail": f"Actions are suspiciously regular (~{avg_gap:.0f}s apart)"
            })

        # check for super fast actions
        fast_actions = sum(1 for g in gaps if g < MIN_ACTIVITY_GAP_SECONDS)
        if fast_actions > 3:
            flags.append({
                "type": "rapid_fire",
                "detail": f"{fast_actions} actions faster than {MIN_ACTIVITY_GAP_SECONDS}s apart"
            })

    return flags


async def _check_content_spam(db: AsyncSession, user_id: str) -> list:
    """Check for low-effort or duplicate content submissions."""
    flags = []

    result = await db.execute(
        select(ActivityLog).where(
            ActivityLog.user_id == user_id,
            ActivityLog.action == "content_submitted"
        ).order_by(ActivityLog.created_at.desc()).limit(10)
    )
    content_logs = result.scalars().all()

    if len(content_logs) < 2:
        return flags

    # check for duplicate content
    contents = []
    for log in content_logs:
        if log.metadata_ and "content" in log.metadata_:
            contents.append(log.metadata_["content"])

    # simple dedup check - if most recent content is very similar to previous
    if len(contents) >= 2:
        for i in range(min(3, len(contents) - 1)):
            similarity = _simple_similarity(contents[0], contents[i+1])
            if similarity > 0.8:
                flags.append({
                    "type": "duplicate_content",
                    "detail": f"Content submission too similar to previous ({similarity:.0%} match)"
                })
                break

    return flags


def _simple_similarity(a: str, b: str) -> float:
    """Quick and dirty text similarity. Not perfect but good enough for flagging."""
    if not a or not b:
        return 0.0
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    shared = a_words & b_words
    return len(shared) / max(len(a_words), len(b_words))


def _calculate_risk(flags: list) -> str:
    """Turn flags into a risk level."""
    if not flags:
        return "low"
    if len(flags) >= 3:
        return "critical"
    if any(f["type"] == "bot_pattern" for f in flags):
        return "high"
    if len(flags) >= 2:
        return "high"
    return "medium"
