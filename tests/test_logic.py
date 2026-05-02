"""
Tests for the core logic modules - scoring, streaks, fraud detection.
Run with: poetry run pytest tests/ -v
"""
import pytest
from app.logic.scoring import _mock_score, score_to_points
from app.logic.streaks import get_multiplier, STREAK_BONUSES
from app.logic.fraud import _simple_similarity, _calculate_risk
from app.logic.reputation import get_tier, get_reward_multiplier, ACTION_WEIGHTS
from app.logic.quests import HIDDEN_QUESTS


# --- Scoring Tests ---

class TestScoring:
    def test_mock_score_short_content(self):
        """Short content should get a lower score."""
        result = _mock_score("hi")
        assert result["score"] < 60

    def test_mock_score_long_content(self):
        """Longer, varied content should score higher."""
        content = "This is a well-thought-out piece about community building. " \
                  "It covers engagement strategies, retention tactics, and growth loops. " \
                  "The key insight is that gamification works when it feels natural."
        result = _mock_score(content)
        assert result["score"] > 40

    def test_mock_score_spammy_content(self):
        """Spam-like content should score lower."""
        result = _mock_score("FREE MONEY!!! CLICK HERE!!! NOW!!! WOW!!!")
        assert result["score"] < 70

    def test_score_to_points_great(self):
        assert score_to_points(90) == 25

    def test_score_to_points_decent(self):
        assert score_to_points(65) == 15

    def test_score_to_points_meh(self):
        assert score_to_points(45) == 8

    def test_score_to_points_terrible(self):
        assert score_to_points(20) == 3


# --- Streak Tests ---

class TestStreaks:
    def test_multiplier_under_7(self):
        assert get_multiplier(1) == 1.0
        assert get_multiplier(5) == 1.0

    def test_multiplier_at_7(self):
        assert get_multiplier(7) == 1.5

    def test_multiplier_above_7(self):
        assert get_multiplier(30) == 1.5

    def test_streak_bonuses_exist(self):
        assert 3 in STREAK_BONUSES
        assert 7 in STREAK_BONUSES
        assert STREAK_BONUSES[7] > STREAK_BONUSES[3]


# --- Fraud Detection Tests ---

class TestFraudDetection:
    def test_similarity_identical(self):
        assert _simple_similarity("hello world", "hello world") == 1.0

    def test_similarity_different(self):
        sim = _simple_similarity("hello world", "completely different text here")
        assert sim < 0.5

    def test_similarity_empty(self):
        assert _simple_similarity("", "hello") == 0.0
        assert _simple_similarity("hello", "") == 0.0

    def test_risk_no_flags(self):
        assert _calculate_risk([]) == "low"

    def test_risk_one_flag(self):
        assert _calculate_risk([{"type": "referral_spam_daily", "detail": "test"}]) == "medium"

    def test_risk_bot_pattern(self):
        assert _calculate_risk([{"type": "bot_pattern", "detail": "test"}]) == "high"

    def test_risk_critical(self):
        flags = [{"type": f"flag_{i}", "detail": "test"} for i in range(3)]
        assert _calculate_risk(flags) == "critical"


# --- Reputation Tests ---

class TestReputation:
    def test_tier_newcomer(self):
        assert get_tier(5) == "newcomer"

    def test_tier_member(self):
        assert get_tier(30) == "member"

    def test_tier_veteran(self):
        assert get_tier(75) == "veteran"

    def test_tier_elite(self):
        assert get_tier(150) == "elite"

    def test_reward_multiplier_newcomer(self):
        assert get_reward_multiplier(5) == 1.0

    def test_reward_multiplier_elite(self):
        assert get_reward_multiplier(150) == 1.5


# --- Hidden Quests Tests ---

class TestQuests:
    def test_quest_conditions_exist(self):
        for key, quest in HIDDEN_QUESTS.items():
            assert "name" in quest
            assert "points" in quest
            assert "condition" in quest
            assert callable(quest["condition"])

    def test_first_referral_condition(self):
        cond = HIDDEN_QUESTS["first_referral"]["condition"]
        assert cond({"referrals": 0}) == False
        assert cond({"referrals": 1}) == True

    def test_streak_master_condition(self):
        cond = HIDDEN_QUESTS["streak_master"]["condition"]
        assert cond({"streak": 5}) == False
        assert cond({"streak": 7}) == True
