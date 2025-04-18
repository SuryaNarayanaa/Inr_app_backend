from fastapi import APIRouter, Depends, Request, HTTPException,Form,UploadFile,File,Query,Body
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.utils.authutils import get_current_user, role_required
from app.model import INRReport
from app.utils.patientUtils import calculate_monthly_inr_average, get_medication_dates, find_missed_doses
from app.database import patient_collection,doctor_collection
import os
from datetime import datetime, timedelta,date
import base64


async def patient_home(request: Request, current_user: dict = Depends(role_required("patient"))):
    pipeline = [
    {
        "$match": {
            "ID": current_user["ID"],
        }
    },
    {
        "$lookup": {
            "from": "doctors",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }
    },
    {
        "$lookup": {
            "from": "doctors",
            "localField": "doctor",
            "foreignField": "ID",
            "as": "doctor_info"
        }
    },
    {
        "$unwind": {"path": "$caretaker_info", "preserveNullAndEmptyArrays": True}
    },
    {
        "$unwind": {"path": "$doctor_info", "preserveNullAndEmptyArrays": True}
    },
    {
        "$addFields": {
            "caretakerName": "$caretaker_info.fullname",
            "doctorName": "$doctor_info.fullname"
        }
    },
    {
            "$unset": ["doctor_info", "caretaker_info"]
    }
    ]
    patient = await patient_collection.aggregate(pipeline).to_list(length=1)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    pat = patient[0];
    if not pat.get("inr_reports"):
        pat["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]
    print(pat.get("inr_reports"))
    chart_data = calculate_monthly_inr_average(pat.get("inr_reports"))

    therapy_start_date = pat.get("therapy_start_date")
    dosage_schedule = pat.get("dosage_schedule", [])

    if not therapy_start_date or not dosage_schedule:
        raise HTTPException(status_code=400, detail="Therapy start date or dosage schedule is missing")

    medication_dates = get_medication_dates(therapy_start_date, dosage_schedule)
    missed_doses = find_missed_doses(medication_dates, pat.get("taken_doses"))[-1:-11:-1]

    json_encoded_pat = jsonable_encoder(pat, exclude={"_id": True,"passHash":True,"refresh_token":True})
    return JSONResponse(
        status_code=200,
        content={
            "patient": json_encoded_pat,
            "chart_data": chart_data,
            "missed_doses": missed_doses
        }
    )

async def update_inr_report(request:Request,
        inr_value: float = Form(...),location_of_test: str = Form(...),
        date: str = Form(...),file:str = Form(...),
        file_name:str = Form(...),
        current_user: dict = Depends(role_required("patient"))):
    file_path = f"static/patient_docs/{file_name}"
    missing_padding = len(file) % 4
    if missing_padding:
        file += '=' * (4 - missing_padding)
    file_bytes = base64.b64decode(file)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    
    report_dict:INRReport = {
        "inr_value": inr_value,
        "location_of_test": location_of_test,
        "date": date,
        "file_name": file_name,
        "file_path": file_path,
        "type": "INR Report",
    }
    result = await patient_collection.update_one(
        {"ID":current_user["ID"]},
        {"$push": {"inr_reports": report_dict}}
    )
    if result.matched_count == 0:
        os.remove(file_path)
        raise HTTPException(status_code=404, detail="Patient not found")
    return JSONResponse(
        status_code=200,
        content={"message": "INR report added successfully", "report": report_dict})

async def patient_reports(request:Request, current_user: dict = Depends(role_required("patient"))):
    data = {
        "lifestyleChanges": current_user.get("lifestylechanges"),
        "otherMedication": current_user.get("othermedication"),
        "sideEffects": current_user.get("sideeffects"),
        "prolongedIllness": current_user.get("prolongedillness")
    }
    return JSONResponse(status_code=200, content=data)

async def submit_report(request: Request, 
    typ: str = Query(..., description="type of report to change"),
    field: str = Form(...),
    current_user: dict = Depends(role_required("patient"))):
    print(typ.lower())
    if typ.lower() not in ["lifestylechanges", "othermedication", "sideeffects", "prolongedillness"]:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    result = await patient_collection.update_one(
        {"ID": current_user["ID"]},
        {"$set": {typ: field }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return JSONResponse(status_code=200, content={"message": "Report submitted successfully"})

async def get_missed_doses(request: Request, current_user: dict = Depends(role_required("patient"))):
    therapy_start_date = current_user.get("therapy_start_date")
    dosage_schedule = current_user.get("dosage_schedule", [])

    if not therapy_start_date or not dosage_schedule:
        raise HTTPException(status_code=400, detail="Therapy start date or dosage schedule is missing")

    medication_dates = get_medication_dates(therapy_start_date, dosage_schedule)
    missed_doses = find_missed_doses(medication_dates, current_user.get("taken_doses"))

    recent_missed_doses = []
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    for date in missed_doses:
        date_obj = datetime.strptime(date, "%d-%m-%Y")
        if seven_days_ago <= date_obj <= today:
            recent_missed_doses.append(date)
            missed_doses.remove(date)
    return JSONResponse(status_code=200, content={"recent_missed_doses":recent_missed_doses,"missed_doses": missed_doses})

async def take_dose (request: Request,date:str,current_user: dict = Depends(role_required("patient"))):
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    date_obj = datetime.combine(date, datetime.min.time())
    if not (seven_days_ago <= date_obj <= today):
        raise HTTPException(status_code=400, detail="Date is not within the last 7 days")
    if date_obj.strftime("%Y-%m-%d") in current_user["taken_doses"]:
        raise HTTPException(status_code=400, detail="Dose already taken for this date")
    
    date_str = date_obj.strftime("%Y-%m-%d")
    result = await patient_collection.update_one(
        {"ID": current_user["ID"]},
        {"$push": {"taken_doses": date_str}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Dose already taken for this date")
    return JSONResponse(status_code=200, content={"message": "Dose taken successfully"})