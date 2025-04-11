from fastapi import  Depends, Request, HTTPException,Query
from fastapi.responses import JSONResponse,FileResponse
from app.utils.authutils import role_required,get_current_user
from app.database import patient_collection,doctor_collection
from app.model import Patient,DosageSchedule
from app.utils.patientUtils import calculate_monthly_inr_average,find_missed_doses,get_medication_dates
from typing import List
from datetime import datetime
import pytz
import os

async def doctorhome(request:Request,current_user : dict = Depends(role_required("doctor"))):
    current_user["_id"] = str(current_user["_id"])
    current_user.pop("passHash",None)
    current_user.pop("refresh_token",None)
    return JSONResponse(status_code=200, content={"doctor":current_user})


async def get_doctors():  # review why this route
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
    print(updated_result)
    if updated_result.matched_count == 0:
        print("Inside here")
        raise HTTPException(status_code=404, detail="Patient not found")
    if updated_result.modified_count == 0:
        print("Inside here 2") 
        raise HTTPException(status_code=400, detail="Doctor reassignment failed")
    print("sending response")
    return JSONResponse(
        status_code=200,
        content={"message": "Doctor reassigned successfully", "patientID": patient_id, "newDoctorID": doc})

#review This route 
async def add_patient(patient_id:str,request:Request,current_user:dict = Depends(role_required("doctor"))):
    patient = patient_collection.find({"ID":patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

async def get_patients(request:Request,current_user:dict = Depends(role_required("doctor"))):
    pipeline = [
        {"$match": {"doctor": current_user["ID"]}},
        {"$lookup": {
            "from": "items",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
    ]
    patients = await patient_collection.aggregate(pipeline).to_list(length=None)
    if len(patients) == 0:
        patients = await patient_collection.find(
            {"doctor": current_user["ID"], "caretaker": {"$exists": False}}
        ).to_list(length=None)
    for patient in patients:
        if "_id" in patient:
            patient["_id"] = str(patient["_id"])
    return JSONResponse(status_code=200, content={"patients": patients})

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
        patient["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]
    patient["_id"] = str(patient["_id"])
    patient = dict(patient)
    return JSONResponse(
        status_code=200,
        content={
            "patient": patient, 
            "user": current_user,
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

