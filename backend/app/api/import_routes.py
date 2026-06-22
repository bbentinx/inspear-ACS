from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..api.deps import get_current_user
from ..services.import_csv import import_customers_csv, import_devices_csv, ImportResult

router = APIRouter(prefix="/import", tags=["import"])


class ImportResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[str]


@router.post("/customers", response_model=ImportResponse)
async def import_customers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Arquivo deve ser .csv")
    content = (await file.read()).decode("utf-8-sig")
    result: ImportResult = await import_customers_csv(db, content)
    return ImportResponse(**result.__dict__)


@router.post("/devices", response_model=ImportResponse)
async def import_devices(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Arquivo deve ser .csv")
    content = (await file.read()).decode("utf-8-sig")
    result: ImportResult = await import_devices_csv(db, content)
    return ImportResponse(**result.__dict__)