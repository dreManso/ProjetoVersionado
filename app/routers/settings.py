from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting
from ..schemas import SettingsIn
from ..services import get_setting

router = APIRouter()


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    return {"ifood_fee_percent": get_setting(db, "ifood_fee_percent")}


@router.put("")
def save_settings(data: SettingsIn, db: Session = Depends(get_db)):
    row = db.get(Setting, "ifood_fee_percent") or Setting(key="ifood_fee_percent", value="30")
    row.value = str(data.ifood_fee_percent)
    db.add(row)
    db.commit()
    return read_settings(db)
