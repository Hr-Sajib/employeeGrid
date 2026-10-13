import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import func
from src.usage.model import UsageLog
from src.utils.settings import settings

# Kept in memory, so they reset when the server restarts and are per process. The daily spend is reloaded from the database.
recent = defaultdict(deque)   # user id -> times of the last messages
spent = {}                    # user id -> (UTC date, dollars spent that day)


def today():
    return datetime.now(timezone.utc).date()


def check(db, user) -> None:
    """Raises 429 if the user sent too many messages this minute or used up today's budget."""
    now = time.time()
    window = recent[user.id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(429, f"Too many messages. Please wait about {int(60 - (now - window[0])) + 1} seconds.")

    day, cost = spent.get(user.id, (None, 0.0))
    if day != today():
        start = datetime.combine(today(), datetime.min.time())
        cost = db.query(func.coalesce(func.sum(UsageLog.cost_usd), 0.0)).filter(UsageLog.user_id == user.id, UsageLog.created_at >= start).scalar()
        spent[user.id] = (today(), cost)
    if cost >= settings.DAILY_BUDGET_USD:
        raise HTTPException(429, "Your daily usage budget is used up. It resets at midnight UTC.")
    window.append(now)


def add_cost(user_id, amount: float) -> None:
    day, cost = spent.get(user_id, (today(), 0.0))
    spent[user_id] = (today(), cost + amount)
