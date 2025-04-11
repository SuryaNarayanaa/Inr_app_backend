from typing import List, Dict, Optional
from pydantic import BaseModel, Field, constr
from datetime import date, datetime
from bson import ObjectId

# Helper class for MongoDB ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class PatientCreate(BaseModel):
    name: str = Field(..., pattern=r'^PAT', min_length=4, strip_whitespace=True)  # Should contain "PAT" prefix
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    age: int = Field(..., ge=1, le=120)
    gender: str = Field(..., pattern="^(M|F|O)$")
    caretaker: Optional[str] = None  # Caretaker ID if exists
    type: str = "Patient"
    refresh_token: Optional[str] = None  # Refresh token for JWT

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True  # Allow using `_id` when interacting with MongoDB

class DoctorCreate(BaseModel):
    ID: str = Field(..., pattern=r'^DOC', min_length=4, strip_whitespace=True)  # Enforce DOC prefix
    fullName: str
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    password: str  # Raw password to be hashed
    type: str = "Doctor"  # Auto-set for consistency
    refresh_token: Optional[str] = None  # Refresh token for JWT

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class MedicalHistory(BaseModel):
    diagnosis: str
    duration_value: int
    duration_unit: str

class DosageSchedule(BaseModel):
    day: str
    dosage: float

    def as_dict(self) -> dict:
        return {"day": self.day, "dosage": self.dosage}

class Patient(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    age: int = Field(..., ge=1, le=120)
    gender: str = Field(..., pattern="^(M|F|O)$")
    target_inr_min: float
    target_inr_max: float
    therapy: str
    medical_history: List[MedicalHistory]
    therapy_start_date: date
    dosage_schedule: List[DosageSchedule]
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    kin_name: str = Field(..., pattern="^[a-zA-Z ]{2,}$")
    kin_contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    refresh_token: Optional[str] = None  # Refresh token for JWT

    def as_dict(self) -> Dict:
        dct = self.dict(by_alias=True)
        dct["therapy_start_date"] = datetime.strftime(dct["therapy_start_date"], "%d/%m/%Y")
        return dct

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class Doctor(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    fullName: str
    ID: str
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    refresh_token: Optional[str] = None  # Refresh token for JWT

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class INRReport(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    type: str = Field(default="INR Report")
    inr_value: float
    location_of_test: str
    date: datetime
    file_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}