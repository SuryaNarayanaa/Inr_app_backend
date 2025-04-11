from fastapi import  Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from app.utils.authutils import get_current_user, role_required
from app.model import INRReport
from app.utils.patientUtils import calculate_monthly_inr_average, get_medication_dates, find_missed_doses


async def patient_home(request: Request, current_user: dict = Depends(role_required("patient"))):
    pat = current_user

    if not pat.get("inr_reports"):
        pat["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]

    chart_data = calculate_monthly_inr_average(pat.get("inr_reports"))

    # Get missed doses
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