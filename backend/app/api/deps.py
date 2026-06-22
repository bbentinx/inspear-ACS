from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..config import settings
from ..services.auth import decode_token, get_user_by_id
from ..models.entities import User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not getattr(settings, "auth_enabled", True):
        # Modo dev sem auth — retorna usuário fictício
        class FakeUser:
            id = "dev"
            email = "dev@local"
            name = "Dev"
            role = "admin"
        return FakeUser()  # type: ignore

    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token não fornecido")
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado")
    return user


async def verify_api_key(api_key: str | None = Depends(api_key_header)) -> bool:
    """Valida API key para endpoints de ingestão (ACS/GenieACS)."""
    expected = getattr(settings, "inspear_api_key", "") or settings.secret_key
    if not expected:
        return True
    if api_key != expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key inválida")
    return True