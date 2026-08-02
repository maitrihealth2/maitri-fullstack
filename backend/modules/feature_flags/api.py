from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database.models import get_db, FeatureFlag, UserFeatureAccess, User
from security.authentication.api import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/features", tags=["features"])

class FeatureResponse(BaseModel):
    features: List[str]

@router.get("/my-flags", response_model=FeatureResponse)
def get_my_features(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns a list of feature names that the current user has access to.
    This checks global flags + beta-user specific access.
    """
    # Get all globally active features
    global_flags = db.query(FeatureFlag).filter(FeatureFlag.is_active_for_all == True).all()
    feature_names = {f.feature_name for f in global_flags}

    # Get features specific to this beta user
    user_access = db.query(UserFeatureAccess).filter(UserFeatureAccess.user_id == current_user.id).all()
    for access in user_access:
        feature_names.add(access.feature_name)

    return FeatureResponse(features=list(feature_names))
