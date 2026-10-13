from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.auth.deps import require_admin
from src.usage.controller import UsageController
from src.utils.db import get_db

usage_routes = APIRouter(prefix="/usage", tags=["usage"], dependencies=[Depends(require_admin)])


@usage_routes.get("")
def usage_summary(db: Session = Depends(get_db)):
    return UsageController.summary(db)
