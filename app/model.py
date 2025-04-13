from typing import List, Dict, Optional
from pydantic import BaseModel, Field, constr, field_validator
from datetime import date, datetime
from bson import ObjectId

# Helper class for MongoDB ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

class MedicalHistory(BaseModel):
    diagnosis: str
    duration_value: int
    duration_unit: str

class DosageSchedule(BaseModel):
    day: str
    dosage: float

    def as_dict(self) -> dict:
        return {"day": self.day, "dosage": self.dosage}


class PatientCreate(BaseModel):
    name:str
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    age: int = Field(..., ge=1, le=120)
    gender: str = Field(..., pattern="^(M|F|O)$")
    type: str = "Patient"
    therapy_start_date : date
    target_inr_min:float
    target_inr_max: float
    therapy: str
    medical_history: Optional[List[MedicalHistory]]
    therapy_start_date: date
    dosage_schedule: Optional[List[DosageSchedule]]
    
    @field_validator("contact",mode='before')
    @classmethod
    def validate_contact(cls, v):
        if not v.startswith("+91"):
            raise ValueError("Contact number must start with +91")
        if len(v) != 13 or not v[3:].isdigit():
            raise ValueError("Contact number must be 10 digits long after +91")
        return v
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
    
    def as_dict(self) -> Dict:
        dct = self.dict(by_alias=True)
        dct["therapy_start_date"] = datetime.strftime(dct["therapy_start_date"], "%d/%m/%Y")
        return dct

class DoctorCreate(BaseModel):
    ID: str = Field(..., pattern=r'^DOC', min_length=4, strip_whitespace=True)  # Enforce DOC prefix
    fullName: str
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    password: str  # Raw password to be hashed
    occupation:str
    type: str = "Doctor"  # Auto-set for consistency
    refresh_token: Optional[str] = None  # Refresh token for JWT

    class Config:
        populate_by_name = True
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
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Patient(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    ID : str
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
    doctor : str
    caretaker: str
    inr_reports:List[INRReport]


    def as_dict(self) -> Dict:
        dct = self.dict(by_alias=True)
        dct["therapy_start_date"] = datetime.strftime(dct["therapy_start_date"], "%d/%m/%Y")
        return dct

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Doctor(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    fullName: str
    ID: str
    PFP:str
    contact: str = Field(..., pattern=r"^\+91\s?(\d\s?){10}$")
    occupation:str
    refresh_token: Optional[str] = None  # Refresh token for JWT

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
