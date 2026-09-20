from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.repositories.social import SocialRepository
from app.db.session import get_db_session


def get_repository(session: Session = Depends(get_db_session)) -> SocialRepository:
    return SocialRepository(session)

