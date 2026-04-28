"""
AI Content Scoring - uses OpenAI to evaluate user submissions.

We check for originality, engagement potential, relevance, and effort.
Spam or lazy AI-generated fluff gets a low score.
"""
from openai import AsyncOpenAI
from app.config import settings

# openrouter uses the same SDK, just different base URL
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

SCORING_PROMPT = """You are a content quality evaluator for a community engagement platform.
Score this content on a scale of 0-100 based on:
- Originality (is it unique or copy-pasted?)
- Engagement potential (would people interact with this?)
- Relevance (is it on-topic?)
- Effort (did they put thought into it?)

Content to evaluate:
{content}

Respond with ONLY a JSON object like: {{"score": 75, "reason": "brief explanation"}}"""


async def score_content(content: str) -> dict:
    """
    Send content to OpenAI for scoring.
    Returns {score: 0-100, reason: "why this score"}
    """
    if settings.OPENAI_API_KEY == "mock-key":
        # mock mode for dev - just return a basic score based on length
        return _mock_score(content)

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",  # openrouter model format
            messages=[
                {"role": "system", "content": "You are a content quality evaluator. Respond only with JSON."},
                {"role": "user", "content": SCORING_PROMPT.format(content=content)}
            ],
            temperature=0.3,
            max_tokens=100,
        )

        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "score": min(max(result.get("score", 50), 0), 100),
            "reason": result.get("reason", "")
        }
    except Exception as e:
        # if openai fails, fall back to simple scoring
        return {"score": _fallback_score(content), "reason": f"AI scoring unavailable, used fallback"}


def _mock_score(content: str) -> dict:
    """Simple scoring when we don't have an API key."""
    score = 30  # baseline

    # length = effort (mostly)
    if len(content) > 50:
        score += 15
    if len(content) > 200:
        score += 15

    # no spam indicators
    if content.count("!") < 5 and content.count("??") < 3:
        score += 10

    # has substance
    words = content.split()
    unique_words = set(words)
    if len(unique_words) / max(len(words), 1) > 0.6:
        score += 10  # decent vocabulary variety

    return {"score": min(score, 100), "reason": "Mock scoring (no API key)"}


def _fallback_score(content: str) -> int:
    """Last resort scoring if AI completely fails."""
    return min(len(content) // 2, 80)  # rough: longer = more effort


def score_to_points(score: int) -> int:
    """Convert a 0-100 score to point reward."""
    if score >= 80:
        return 25  # great content
    if score >= 60:
        return 15  # decent
    if score >= 40:
        return 8   # meh
    return 3       # barely anything
