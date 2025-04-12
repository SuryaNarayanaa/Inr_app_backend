from fastapi import  Depends, Request, HTTPException,Form,UploadFile,File,Query
from fastapi.responses import JSONResponse
from app.utils.authutils import get_current_user, role_required
from app.model import INRReport
from app.utils.patientUtils import calculate_monthly_inr_average, get_medication_dates, find_missed_doses
from app.database import patient_collection,doctor_collection
import os

async def patient_home(request: Request, current_user: dict = Depends(role_required("patient"))):
    pat = current_user

    if not pat.get("inr_reports"):
        pat["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]

    chart_data = calculate_monthly_inr_average(pat.get("inr_reports"))

    therapy_start_date = pat.get("therapy_start_date")
    dosage_schedule = pat.get("dosage_schedule", [])

    if not therapy_start_date or not dosage_schedule:
        raise HTTPException(status_code=400, detail="Therapy start date or dosage schedule is missing")

    medication_dates = get_medication_dates(therapy_start_date, dosage_schedule)
    missed_doses = find_missed_doses(medication_dates, pat.get("taken_doses"))[-1:-11:-1]

    return JSONResponse(
        status_code=200,
        content={
            "patient": pat,
            "chart_data": chart_data,
            "missed_doses": missed_doses
        }
    )

async def update_inr_report(request:Request,
        inr_value: float = Form(...),location_of_test: str = Form(...),
        date: str = Form(...),file:UploadFile = File(...),
        current_user: dict = Depends(role_required("patient"))):
    file_path = f"static/patient_docs/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    report_dict:INRReport = {
        "inr_value": inr_value,
        "location_of_test": location_of_test,
        "date": date,
        "file_name": file.filename,
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
        "lifestyleChanges": current_user.get("lifestyleChanges"),
        "otherMedication": current_user.get("otherMedication"),
        "sideEffects": current_user.get("sideEffects"),
        "prolongedIllness": current_user.get("prolongedIllness")
    }
    return JSONResponse(status_code=200, content=data)

async def submit_report(request: Request, 
    typ: str = Query(..., description="type of report to change"),
    field: str = Form(...),
    current_user: dict = Depends(role_required("patient"))):
    if typ.lower() not in ["lifestyleChanges", "otherMedication", "sideEffects", "prolongedIllness"]:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    result = await patient_collection.update_one({
        {"ID": current_user["ID"]},
        {"$set": {typ: field }}
    })

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

    return JSONResponse(status_code=200, content={"missed_doses": missed_doses})

async def take_dose (date: str, request: Request, current_user: dict = Depends(role_required("patient"))):
    # TODO : figure out The logic for this function. It is not clear from the original code what it should do.
    return JSONResponse(status_code=200, content={"message": "Dose taken successfully"})