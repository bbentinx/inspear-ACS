from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..models.entities import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    r = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = r.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    r = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    return r.scalar_one_or_none()


async def ensure_admin_user(db: AsyncSession):
    """Cria usuário admin padrão se não existir."""
    from ..config import settings as s
    admin_email = getattr(s, "admin_email", "admin@inspear.local")
    admin_password = getattr(s, "admin_password", "admin123")
    r = await db.execute(select(User).where(User.email == admin_email))
    if r.scalar_one_or_none():
        return
    user = User(
        email=admin_email,
        name="Administrador",
        password_hash=hash_password(admin_password),
        role="admin",
    )
    db.add(user)
    await db.commit()
    print(f"[auth] Admin criado: {admin_email}")