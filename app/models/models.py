import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String)
    points = Column(Integer, default=0)
    reputation_score = Column(Float, default=0.0)
    streak = Column(Integer, default=0)
    last_active = Column(Date, default=datetime.date.today)
    # silently flagged if fraud suspected
    fraud_flag = Column(Boolean, default=False)
    # shadow restrict rewards without telling user
    shadow_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("UserTask", back_populates="user")
    activity = relationship("ActivityLog", back_populates="user")
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(String, ForeignKey("users.discord_id"))
    referred_user = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, validated, rejected
    quality_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    points = Column(Integer, default=0)
    # referral, content, participation, hidden
    type = Column(String, default="participation")
    hidden = Column(Boolean, default=False)
    # condition to unlock hidden quests
    unlock_condition = Column(JSON, nullable=True)

    user_tasks = relationship("UserTask", back_populates="task")


class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.discord_id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    status = Column(String, default="in_progress")  # in_progress, completed, failed
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
    task = relationship("Task", back_populates="user_tasks")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.discord_id"))
    # referral_submitted, content_posted, task_completed, streak_updated, etc
    action = Column(String, nullable=False)
    # flexible data storage for whatever context we need
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="activity")
