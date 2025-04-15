from fastapi import  Depends, Request, HTTPException,Query
from fastapi.responses import JSONResponse,FileResponse
from fastapi.encoders import jsonable_encoder
from app.utils.authutils import role_required,get_current_user
from app.database import patient_collection,doctor_collection
from app.model import Patient,DosageSchedule,PatientCreate
from app.utils.patientUtils import calculate_monthly_inr_average,find_missed_doses,get_medication_dates
from typing import List
from datetime import datetime, date
import pytz
import os
import re
import hashlib

async def doctorhome(request:Request,current_user : dict = Depends(role_required("doctor"))):
    pipeline = [
    {"$match": {"doctor": current_user["ID"]}},
    {"$lookup": {
        "from": "doctor",
        "localField": "caretaker",
        "foreignField": "ID",
        "as": "caretaker_info"
    }},
    {"$unwind": {"path": "$caretaker_info", "preserveNullAndEmptyArrays": True}},
    {"$addFields": {"caretakerName": "$caretaker_info.fullName"}},
    {"$project": {"caretakerName": 1, "name": 1, "doctor": 1, "ID": 1, "age": 1, "gender": 1}}
    ]
    patients = await patient_collection.aggregate(pipeline).to_list(length=None)
    patients2 = await patient_collection.find(
        {"doctor": current_user["ID"],"caretaker": {"$exists": False}},
        {"name": 1, "gender": 1, "doctor": 1, "ID": 1, "age": 1}
    ).to_list(length=None)
    for i in patients2:
        patients.append(i)
    for patient in patients:
        if "_id" in patient:
            patient["_id"] = str(patient["_id"])
    json_user = jsonable_encoder(current_user,exclude={"passHash","refresh_token","_id"})
    return JSONResponse(status_code=200, content={"patients":patients,"user":json_user})


async def get_doctors():
    doctors = await doctor_collection.find({},{"_id":0,"fullname":1,"ID":1}).to_list(length=None)
    if( not doctors):
        raise HTTPException(status_code=404, detail="No doctors found")
    return JSONResponse( status_code=200, content={"doctors": doctors} )

async def reassign_doctor(patient_id:str,
        doc:str = Query(...,description="New Doctor or CareTakerId"),
        typ:str = Query(...,description="Doctor or CareTaker?"),
        current_user:dict = Depends(get_current_user)):
    if typ.lower() not in ["doctor","caretaker"]:
        raise HTTPException(status_code=400, detail="Invalid type. Must be 'doctor' or 'caretaker'.")
    doctor = await doctor_collection.find_one({"ID":doc})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    patient = await patient_collection.find_one({"ID":patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    updated_result = await patient_collection.update_one(
        {"ID":patient_id},
        {"$set":{typ:doc}}
    )
    if updated_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    if updated_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Doctor reassignment failed")
    return JSONResponse(
        status_code=200,
        content={"message": "Doctor reassigned successfully", "patientID": patient_id, "newDoctorID": doc})

async def add_patient(patient_data:PatientCreate,request:Request,current_user:dict = Depends(role_required("doctor"))):
    patient_data = patient_data if isinstance(patient_data, dict) else patient_data.dict()   
    existing_patient = await patient_collection.find_one({"contact": patient_data["contact"]})
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient already exists")
    if patient_data.get("caretaker"):
        caretaker = await doctor_collection.find_one({"ID": patient_data["caretaker"]})
        if not caretaker:
            raise HTTPException(status_code=400, detail="Caretaker does not exist in db")
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
    if isinstance(patient_data["therapy_start_date"], date):
        patient_data["therapy_start_date"] = datetime.combine(
        patient_data["therapy_start_date"], datetime.min.time()
    )

    
    cleaned_contact = patient_data["contact"].replace(" ", "").replace("+91", "")
    patient_data["passHash"] = hashlib.sha512(cleaned_contact.encode()).hexdigest()
    patient_data["doctor"] = current_user["ID"]
    result = await patient_collection.insert_one(patient_data)
    return JSONResponse (status_code=200,
        content={"message": "Patient created successfully","patient_id":patient_id})

async def get_patients(request:Request,current_user:dict = Depends(role_required("doctor"))):
    pipeline = [
        {"$match": {"doctor": current_user["ID"]}},
        {"$lookup": {
            "from": "doctor",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
    ]
    patients = await patient_collection.aggregate(pipeline).to_list(length=None)
    if len(patients) == 0:
        patients2 = await patient_collection.find(
            {"doctor": current_user["ID"], "caretaker": {"$exists": False}}
        ).to_list(length=None)
    for i in patients2:
        patients.append(i)
    json_ready_patients = jsonable_encoder(patients,exclude={"_id","passHash","refresh_token"})
    return JSONResponse(status_code=200, content={"patients":json_ready_patients})

async def view_patient(patient_id:str,request:Request,current_user: dict = Depends(role_required("doctor"))):
    pipeline = [
        {"$match": {"ID":patient_id,"doctor": current_user["ID"]}},
        {"$lookup": {
            "from": "items",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
    ]
    patient = await patient_collection.aggregate(pipeline).to_list(length=None)
    if len(patient) == 0:
        patient = await patient_collection.find_one(
            {"ID":patient_id,"doctor": current_user["ID"], "caretaker": {"$exists": False}}
        )
    else:
        patient = patient[0]
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not patient.get("inr_reports"):
        patient["inr_reports"] = [{"date": str("1900-01-01T00:00"), "inr_value": 0}]
    json_patient = jsonable_encoder(patient,exclude={"_id","passHash","refresh_token"})
    return JSONResponse(
        status_code=200,
        content={
            "patient": json_patient, 
            "chart_data": calculate_monthly_inr_average(patient.get("inr_reports")),
            "missed_doses": find_missed_doses(get_medication_dates(patient.get("therapy_start_date"), patient.get("dosage_schedule")),
                                               patient.get("taken_doses"))
        }) 
    
    
async def edit_dosage(patient_id:str,dosage:List[DosageSchedule],request: Request, current_user: dict = Depends(role_required("doctor"))):
    dosage_list = [i.as_dict() for i in dosage]
    patient = patient_collection.find_one({"ID":patient_id,"doctor": current_user["ID"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_collection.update_one({"ID": patient_id}, {"$set": {"dosage_schedule": dosage_list}})
    return JSONResponse(status_code=200,content={"message": "Dosage edited successfully"})

async def view_reports(typ:str,request:Request,current_user: dict = Depends(role_required("doctor"))):
    if typ == "today":
        patients = patient_collection.find({"doctor": current_user["ID"]})
        report_data = []
        for patient in patients:
            for report in patient["inr_reports",[]]:
                if report["data"].startswith(datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")):
                    report_data.append({
                        "patient_name": patient.get("name"),
                        "inr_report": report,
                    })
        return JSONResponse(status_code=200,content={"reports": report_data}) 
    elif typ == "all":
        patients = patient_collection.find({"doctor": current_user["ID"]})
        report_data = []
        for patient in patients:
            for report in patient["inr_reports",[]]:
                report_data.append({
                    "patient_name": patient.get("name"),
                    "inr_report": report,
                })
        return JSONResponse(status_code=200,content={"reports": report_data})
    else:
        patient = patient_collection.find_one({"ID":typ,"doctor": current_user["ID"]})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        reports = [{"patient_name": patient.get("name"), "inr_report": report} for report in patient["inr_reports"]]
        return JSONResponse(status_code=200,content={"reports": reports})

async def download_patient_report(patient_id:str,request:Request,current_user: dict = Depends(role_required("doctor"))):
    patient = patient_collection.find_one({"ID":patient_id,"doctor": current_user["ID"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not patient.get("inr_reports"):
        raise HTTPException(status_code=404, detail="No reports found")
    inr_reports = patient.get("inr_reports")
    file_path = os.path.join("static/patient_docs", inr_reports.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if inr_reports.filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif inr_reports.filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=415, detail="Unsupported file format")

    return FileResponse(
        path=file_path,
        filename=inr_reports.filename,  
        media_type=media_type    
    )

