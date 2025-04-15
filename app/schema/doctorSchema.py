from pydantic import BaseModel
from app.model import DosageSchedule
from typing import List

class editDosageSchema(BaseModel):
    dosage_schedule : List[DosageSchedule]