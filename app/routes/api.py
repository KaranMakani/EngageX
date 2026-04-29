"""
FastAPI routes - the API layer that n8n and external services call.

These endpoints are what connect n8n workflows to our logic.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from app.database import get_db
from app.models import User, Referral, ActivityLog, Task, UserTask
from app.logic import (
    process_referral, update_streak, detect_fraud,
    score_content, score_to_points, apply_decay,
    check_hidden_quests, process_reengagement,
    calculate_reputation, get_tier
)

router = APIRouter()


# --- request/response models ---

class ReferralRequest(BaseModel):
    referrer_id: str
    referred_user: str

class ContentScoreRequest(BaseModel):
    user_id: str
    content: str

class UserCreateRequest(BaseModel):
    discord_id: str
    username: str

class FraudCheckRequest(BaseModel):
    user_id: str


# --- user endpoints ---

@router.get("/points/{discord_id}")
async def get_points(discord_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user's current points and streak."""
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "points": user.points,
        "streak": user.streak,
        "reputation": user.reputation_score,
        "tier": get_tier(user.reputation_score)
    }


@router.get("/profile/{discord_id}")
async def get_profile(discord_id: str, db: AsyncSession = Depends(get_db)):
    """Full user profile - points, streak, reputation, recent activity."""
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # recent activity
    act_result = await db.execute(
        select(ActivityLog).where(ActivityLog.user_id == discord_id)
        .order_by(desc(ActivityLog.created_at)).limit(10)
    )
    recent = act_result.scalars().all()

    # referral stats
    ref_result = await db.execute(
        select(Referral).where(Referral.referrer_id == discord_id)
    )
    referrals = ref_result.scalars().all()

    return {
        "username": user.username,
        "points": user.points,
        "streak": user.streak,
        "reputation": user.reputation_score,
        "tier": get_tier(user.reputation_score),
        "last_active": str(user.last_active),
        "total_referrals": len(referrals),
        "recent_activity": [
            {"action": a.action, "metadata": a.metadata_, "at": str(a.created_at)}
            for a in recent
        ]
    }


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Top users by points. Weekly resets handled by n8n cron."""
    result = await db.execute(
        select(User).order_by(desc(User.points)).limit(limit)
    )
    users = result.scalars().all()
    return {
        "leaderboard": [
            {"rank": i+1, "username": u.username, "points": u.points, "tier": get_tier(u.reputation_score)}
            for i, u in enumerate(users)
        ]
    }


# --- action endpoints ---

@router.post("/referral")
async def create_referral(req: ReferralRequest, db: AsyncSession = Depends(get_db)):
    """Process a new referral. n8n calls this from the referral form webhook."""
    result = await process_referral(db, req.referrer_id, req.referred_user)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Referral failed"))
    return result


@router.post("/content-score")
async def content_score(req: ContentScoreRequest, db: AsyncSession = Depends(get_db)):
    """Score content submission and award points."""
    # get the user
    result = await db.execute(select(User).where(User.discord_id == req.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # score the content
    scoring = await score_content(req.content)
    points = score_to_points(scoring["score"])

    # apply streak multiplier
    from app.logic.streaks import get_multiplier
    multiplier = get_multiplier(user.streak)
    points = int(points * multiplier)

    # update user
    if not user.shadow_banned:
        user.points += points
    else:
        user.points += points // 3

    # log it
    log = ActivityLog(
        user_id=req.user_id,
        action="content_submitted",
        metadata_={"score": scoring["score"], "points_earned": points, "reason": scoring["reason"]}
    )
    db.add(log)

    # update streak
    await update_streak(db, user)

    # check hidden quests
    await check_hidden_quests(db, user)

    await db.commit()

    return {
        "score": scoring["score"],
        "points_earned": points,
        "reason": scoring["reason"],
        "multiplier_used": multiplier
    }


@router.post("/user")
async def create_user(req: UserCreateRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user. Called when someone joins the Discord server."""
    # check if already exists
    existing = await db.execute(select(User).where(User.discord_id == req.discord_id))
    if existing.scalars().first():
        return {"status": "already_exists"}

    user = User(discord_id=req.discord_id, username=req.username)
    db.add(user)
    await db.commit()
    return {"status": "created", "discord_id": req.discord_id}


# --- n8n webhook endpoints ---

@router.post("/cron/streak-reset")
async def cron_streak_reset(db: AsyncSession = Depends(get_db)):
    """n8n daily cron: reset streaks for inactive users."""
    result = await reset_streaks_daily(db)
    return result


@router.post("/cron/decay")
async def cron_decay(db: AsyncSession = Depends(get_db)):
    """n8n daily cron: apply point decay to inactive users."""
    result = await apply_decay(db)
    return result


@router.post("/cron/reengage")
async def cron_reengage(db: AsyncSession = Depends(get_db)):
    """n8n cron: send re-engagement nudges to inactive users."""
    result = await process_reengagement(db)
    return result


@router.post("/check-fraud")
async def check_fraud(req: FraudCheckRequest, db: AsyncSession = Depends(get_db)):
    """n8n workflow: run fraud detection on a user."""
    result = await detect_fraud(db, req.user_id)
    return result


@router.get("/tasks/{discord_id}")
async def get_user_tasks(discord_id: str, db: AsyncSession = Depends(get_db)):
    """Get available tasks for a user (excludes hidden ones, obviously)."""
    # visible tasks
    result = await db.execute(select(Task).where(Task.hidden == False))
    visible_tasks = result.scalars().all()

    # completed tasks
    done = await db.execute(
        select(UserTask).where(UserTask.user_id == discord_id, UserTask.status == "completed")
    )
    completed = done.scalars().all()
    completed_ids = {ut.task_id for ut in completed}

    return {
        "available": [
            {"id": t.id, "name": t.name, "description": t.description, "points": t.points, "type": t.type}
            for t in visible_tasks if t.id not in completed_ids
        ],
        "completed": [
            {"id": t.id, "name": t.name, "points": t.points}
            for t in visible_tasks if t.id in completed_ids
        ]
    }
