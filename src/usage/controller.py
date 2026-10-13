from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.auth.model import User
from src.usage.model import UsageLog


class UsageController:
    @staticmethod
    def build(user, conversation_id, question: str, run: dict, status: str) -> UsageLog:
        return UsageLog(
            user_id=user.id, conversation_id=conversation_id, question=question[:500], status=status,
            needs_employee_data=run.get("needs_employee_data"), needs_documents=run.get("needs_documents"),
            path=run.get("path"), verdict=run.get("verdict"), retries=run.get("retries", 0),
            total_ms=run.get("total_ms"), llm_calls=run.get("llm_calls"),
            input_tokens=run.get("input_tokens"), output_tokens=run.get("output_tokens"), cost_usd=run.get("cost", 0.0),
        )

    @staticmethod
    def save(db: Session, row: UsageLog) -> None:
        db.add(row)
        db.commit()

    @staticmethod
    def summary(db: Session) -> dict:
        start = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())

        def totals(*filters):
            runs, cost, tokens = db.query(
                func.count(UsageLog.id), func.coalesce(func.sum(UsageLog.cost_usd), 0.0),
                func.coalesce(func.sum(UsageLog.input_tokens + UsageLog.output_tokens), 0),
            ).filter(*filters).one()
            return {"runs": runs, "cost_usd": float(cost), "tokens": int(tokens)}

        by_user = (
            db.query(User.name, User.email, func.count(UsageLog.id), func.coalesce(func.sum(UsageLog.cost_usd), 0.0))
            .join(UsageLog, UsageLog.user_id == User.id).group_by(User.id).order_by(func.sum(UsageLog.cost_usd).desc()).all()
        )
        recent = (
            db.query(UsageLog, User.name).outerjoin(User, User.id == UsageLog.user_id)
            .order_by(UsageLog.created_at.desc()).limit(30).all()
        )
        return {
            "today": totals(UsageLog.created_at >= start),
            "all_time": totals(),
            "by_user": [{"name": n, "email": e, "runs": r, "cost_usd": float(c)} for n, e, r, c in by_user],
            "recent": [
                {"created_at": u.created_at.isoformat(), "user": name or "(removed)", "question": u.question, "path": u.path,
                 "verdict": u.verdict, "status": u.status, "total_ms": u.total_ms, "llm_calls": u.llm_calls, "cost_usd": u.cost_usd}
                for u, name in recent
            ],
        }
