from fastapi import Depends, Request,HTTPException
from fastapi.responses import JSONResponse
from app.utils.authutils import get_current_user, role_required
from app.database import patient_collection, doctor_collection
from app.model import PatientCreate, DoctorCreate 
import hashlib
import re
from typing import Union

async def getadmindetails(request: Request, current_user: dict = Depends(role_required("admin"))):
    patients_cursor = patient_collection.find()
    doctors_cursor = doctor_collection.find()

    patients = await patients_cursor.to_list(length=None)
    doctors = await doctors_cursor.to_list(length=None)

    for patient in patients:
        patient["_id"] = str(patient["_id"])
        patient["role"] = "patient"

    for doctor in doctors:
        doctor["_id"] = str(doctor["_id"])
        doctor["role"] = "doctor"

    all_users = patients + doctors

    # Collect all unique columns
    columns = set()
    for user in all_users:
        columns.update(user.keys())

    # Sort columns: Name, ID, Type, Role, Contact, then everything else
    name_columns = [col for col in columns if 'name' in col.lower() and 'kin' not in col.lower()]
    id_columns = [col for col in columns if col.lower() == "id"]
    type_columns = [col for col in columns if col.lower() == "type"]
    role_columns = [col for col in columns if col.lower() == "role"]
    contact_columns = [col for col in columns if "contact" in col.lower()]
    other_columns = [col for col in columns if col not in name_columns + id_columns + type_columns + role_columns + contact_columns]

    sorted_columns = name_columns + id_columns + type_columns + role_columns + contact_columns + other_columns

    return JSONResponse(
        status_code=200,
        content={"items": all_users, "columns": sorted_columns}
    )


async def create_patient(patient:PatientCreate, current_user: dict = Depends(role_required(["admin"]))):
    
    patient_data = patient if isinstance(patient, dict) else patient.dict()
    
    existing_patient = await patient_collection.find_one({"contact": patient_data["contact"]})
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient already exists")
    
    if "caretaker" in patient_data:
        caretaker = await doctor_collection.find_one({"ID": patient_data["caretaker"]})
        if not caretaker:
            raise HTTPException(status_code=400, detail="Caretaker does not exist")

    latest_patient = await patient_collection.find_one(
        {"ID": {"$regex": "^PAT\\d+$"}},
        sort=[("ID", -1)]
    )

    if latest_patient:
        match = re.search(r"PAT(\d+)", latest_patient["ID"])
        new_suffix = int(match.group(1)) + 1 if match else 1
    else:
        new_suffix = 1

    patient_id = f"PAT{new_suffix:05d}"
    patient_data["ID"] = patient_id

    print(patient_data)
    
    cleaned_contact = patient_data["contact"].replace(" ", "").replace("+91", "")
    patient_data["passHash"] = hashlib.sha512(cleaned_contact.encode()).hexdigest()
    
    result = await patient_collection.insert_one(patient_data)
    print(result)
    return JSONResponse (status_code=200,
        content={"message": "Patient created successfully","patient_id":patient_id})

async def create_doctor(
    doctor: DoctorCreate,
    current_user: dict = Depends(role_required(["admin"]))
):
    existing_doctor = await doctor_collection.find_one({"ID": doctor["ID"]})
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Doctor ID already exists")
    
    hashed_password = hashlib.sha512(doctor["password"].encode('utf-8')).hexdigest()
    
    doctor_data = doctor
    doctor_data.update({
        "passHash": hashed_password,
    })
    
    if "password" in doctor_data:
        doctor_data.pop("password")
    
    result = await doctor_collection.insert_one(doctor_data)
    
    return {
        "message": "Doctor created successfully",
        "doctor_id": str(result.inserted_id)
    }

async def doctor_modify(doctor_id: str, doctor_data: dict, current_user: dict = Depends(role_required(["admin"]))):
    existing_doctor = await doctor_collection.find_one({"ID": doctor_id})
    if not existing_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if "password" in doctor_data:
        hashed_password = hashlib.sha512(doctor_data["password"].encode('utf-8')).hexdigest()
        doctor_data["passHash"] = hashed_password
        doctor_data.pop("password", None) 

    result = await doctor_collection.update_one(
        {"ID": doctor_id},
        {"$set": doctor_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes were made to the doctor")

    return {"message": "Doctor updated successfully", "doctor_id": doctor_id}


async def patient_modify(patient_id: str, patient_data: dict, current_user: dict = Depends(role_required(["admin"]))):
    existing_patient = await patient_collection.find_one({"ID": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # If contact is being updated, hash it for passHash
    if "contact" in patient_data:
        cleaned_contact = patient_data["contact"].replace(" ", "").replace("+91", "")
        patient_data["passHash"] = hashlib.sha512(cleaned_contact.encode()).hexdigest()

    # Update the patient document
    result = await patient_collection.update_one(
        {"ID": patient_id},
        {"$set": patient_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes were made to the patient")

    return {"message": "Patient updated successfully", "patient_id": patient_id}


async def get_patient_by_id(patient_id: str, current_user: dict = Depends(role_required(["admin"]))):
    patient = await patient_collection.find_one({"ID": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient["_id"] = str(patient["_id"])
    patient.pop("passHash", None)
    return patient


async def get_doctor_by_id(doctor_id: str, current_user: dict = Depends(role_required(["admin"]))):
    doctor = await doctor_collection.find_one({"ID": doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor["_id"] = str(doctor["_id"])
    doctor.pop("passHash", None)
    return doctor


async def delete_patient_by_id(patient_id: str, current_user: dict = Depends(role_required(["admin"]))):
    existing_patient = await patient_collection.find_one({"ID": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await patient_collection.delete_one({"ID": patient_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Failed to delete patient")

    return {"message": "Patient deleted successfully", "patient_id": patient_id}


async def delete_doctor_by_id(doctor_id: str, current_user: dict = Depends(role_required(["admin"]))):
    existing_doctor = await doctor_collection.find_one({"ID": doctor_id})
    if not existing_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    result = await doctor_collection.delete_one({"ID": doctor_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Failed to delete doctor")

    return {"message": "Doctor deleted successfully", "doctor_id": doctor_id}