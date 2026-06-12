from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import UserLoginSchema, UserRegisterSchema, TokenSchema
from app.infrastructure.database import get_db
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterSchema, db: Session = Depends(get_db)):
    user_service = UserService(db)
    try:
        user = user_service.register(payload.email, payload.password)
        return {"id": str(user.id), "email": user.email}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/token", response_model=TokenSchema)
def login_for_access_token(payload: UserLoginSchema, db: Session = Depends(get_db)):
    user_service = UserService(db)
    token = user_service.authenticate(payload.email, payload.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": token, "token_type": "bearer"}
