from pydantic import BaseModel, field_validator
from datetime import datetime, date

class DoseInput(BaseModel):
    date: date

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, str):
            for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            raise ValueError("date must be in dd-MM-YYYY or YYYY-MM-DD format")
        return value