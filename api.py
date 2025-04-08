import os
import json
import  hashlib
import uvicorn
import jwt
from datetime import datetime, timedelta
import pytz
from uuid import uuid4, UUID
from typing import List, Dict

from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form, File, UploadFile, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel

from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

from models import *
from utils import *
import secrets

SECRET_KEY = "your-secret-key-here" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(user_data: dict):
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = user_data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token():
    return secrets.token_urlsafe(64)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("ID")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload  
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def role_required(role: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if role != "*" and current_user.get("role") != role:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        return current_user
    return dependency

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("static/patient_docs", exist_ok=True)
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or a list of allowed origins like ["https://myapp.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONGO_URI = "mongodb+srv://flask-access:qwertyuiop@vitalink.ykzz1.mongodb.net/?retryWrites=true&w=majority&appName=db"
client = MongoClient(MONGO_URI)
db = client.get_database("testdb")  
collection = db.get_collection("items")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return JSONResponse(
        status_code=200,
        content={"message": "Hello World."})

@app.post("/login", response_class=HTMLResponse)   
async def login(username: str = Form(...), password: str = Form(...)):
    """Handle user login and return a JWT token."""
    if username == "admin" and password == "admin123":
        user_data = {"name": username, "role": "admin", "ID": username}
        token = create_access_token(user_data)
        return JSONResponse(
            status_code=200,
            content={"message": "login successful", "role": "admin", "access_token": token})
    elif "DOC" in username:
        user = collection.find_one({"ID": username, "type": "Doctor"})
        if user and hashlib.sha512(password.encode('utf-8')).hexdigest() == user["passHash"]:
            user2 = user.copy()
            user2.pop("passHash")
            if "_id" in user2:
                user2["_id"] = str(user2["_id"])
            user2.update({"role": "doctor"})
            token = create_access_token(user2)
            return JSONResponse(
                status_code=200,
                content={"message": "login successful", "role": "doctor", "access_token": token})
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    elif "PAT" in username:
        patient = collection.aggregate([
            {
                "$match": {
                    "type": "Patient",
                    "ID": username
                }
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "caretaker",
                    "foreignField": "ID",
                    "as": "caretaker_info"
                }
            },
            {"$unwind": "$caretaker_info"},
            {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
        ])
        patient = list(patient)
        if len(patient) == 0:
            user = collection.find_one({"type": "Patient", "ID": username, "caretaker": {"$exists": False}})
        if user and password == user["contact"].replace(" ","").replace("+91",""):
            user2 = user.copy()
            if "_id" in user2:
                user2["_id"] = str(user2["_id"])
            user2.update({"role": "patient"})
            token = create_access_token(user2)
            return JSONResponse(
                status_code=200,
                content={"message": "login successful", "role": "patient", "access_token": token})
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/logout", response_class=HTMLResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    return JSONResponse(
        status_code=200,
        content={"message": "logout successful"})

@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def admin_home(request: Request, current_user: dict = Depends(role_required("admin"))):
    items = list(collection.find())
    columns = set()
    for item in items:
        item["_id"] = str(item["_id"])
        columns.update(item.keys())
    name_columns = [col for col in columns if (('name' in col.lower()) and ('kin' not in col.lower()) and ('side' not in col.lower()))]
    id_column = [col for col in columns if 'id' in col.lower()]
    type_column = [col for col in columns if 'type' in col.lower()]
    other_columns = [col for col in columns if col not in name_columns and col not in id_column and col not in type_column]
    sorted_columns = name_columns + id_column + type_column + other_columns

    return JSONResponse(
        status_code=200,
        content={"items": items, "columns": sorted_columns})

@app.get("/item/update/{item_id}", dependencies=[Depends(get_current_user)])
async def get_item(item_id: str, current_user: dict = Depends(role_required("admin"))):
    try:
        item = collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item["_id"] = str(item["_id"])
        item.pop("_id")
        return JSONResponse(
            status_code=200,
            content=item)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching item: {str(e)}")

@app.post("/item/create", dependencies=[Depends(get_current_user)])
async def create_item(item: Item, current_user: dict = Depends(role_required("admin"))):
    item_data = json.loads(item.item)
    collection.insert_one(item_data)
    return {"message": "Item created successfully"}

@app.post("/item/update/{item_id}", dependencies=[Depends(get_current_user)])
async def update_item(item_id: str, item: Item, current_user: dict = Depends(role_required("admin"))):
    item_data = json.loads(item.item)
    result = collection.find_one_and_update(
        {"_id": ObjectId(item_id)}, {"$set": item_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    result["_id"] = str(result["_id"])
    return JSONResponse(
        status_code=200,
        content={"message": "Item updated successfully"})

@app.post("/item/delete/{item_id}", dependencies=[Depends(get_current_user)])
async def delete_item(item_id: str, current_user: dict = Depends(role_required("admin"))):
    result = collection.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(
        status_code=200,
        content={"message": "Item deleted successfully"})

@app.get("/doctor", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def doctor_home(request: Request, current_user: dict = Depends(role_required("doctor"))):
    patients = list(collection.aggregate([
        {"$match": {"type": "Patient", "doctor": current_user["ID"]}},
        {"$lookup": {
            "from": "items",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}},
        {"$project": {"caretakerName": 1, "name": 1, "doctor": 1, "ID": 1, "age": 1, "gender": 1}}
    ]))
    patients2 = list(collection.find({"type": "Patient", "doctor": current_user["ID"], "caretaker": {"$exists": False}}))
    for i in patients2:
        patients.append(i)
    return JSONResponse(
        status_code=200,
        content={"patients": patients, "user": current_user})

@app.get("/doctor/list-api", response_model=List[Doctor])  # noqa:F405
async def get_doctors():
    doctors = list(collection.find({"type": "Doctor"}, {"_id": 0, "fullName": 1, "ID": 1}))
    if not doctors:
        raise HTTPException(status_code=404, detail="No doctors found")
    return JSONResponse(
        status_code=200,
        content=doctors)

@app.post("/doctor/reassign/{patient_id}")
async def reassign_doctor(patient_id: str, 
                          doc: str = Query(..., description="New doctor ID"), 
                          typ: str = Query(..., description="Doctor or Caretaker?"),
                          current_user: dict = Depends(get_current_user)):
    doctor = collection.find_one({"type": "Doctor", "ID": doc})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    update_result = collection.update_one(
        {"type": "Patient", "ID": patient_id},
        {"$set": {typ: doc}}
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    if update_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Doctor reassignment failed")
    return JSONResponse(
        status_code=200,
        content={"message": "Doctor reassigned successfully", "patientID": patient_id, "newDoctorID": doc})

@app.post("/doctor/add-patient", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def add_patient(patient: Patient, request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        patient_data = patient.as_dict()
        patient_data["type"] = "Patient"
        patient_data["doctor"] = current_user["ID"]
        count = collection.count_documents({"type": "patient"})
        new_id = count + 1
        patient_id = f"PAT{new_id:05d}"
        patient_data["ID"] = patient_id
        collection.insert_one(patient_data)
        return {"message": "Success!"}
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"message": "Success? Visit dashboard to confirm."})

@app.get("/doctor/view-patient/{patient_id}", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def view_patient(patient_id: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    patient_cursor = collection.aggregate([
        {"$match": {"type": "Patient", "ID": patient_id}},
        {"$lookup": {
            "from": "items",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
    ])
    patient_list = list(patient_cursor)
    if len(patient_list) == 0:
        patient_list = list(collection.find({"type": "Patient", "doctor": current_user["ID"], "caretaker": {"$exists": False}}))
    patient = patient_list[0]
    if not patient.get("inr_reports"):
        patient["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]
    return JSONResponse(
        status_code=200,
        content={
            "patient": patient, 
            "user": current_user,
            "chart_data": calculate_monthly_inr_average(patient.get("inr_reports")),
            "missed_doses": find_missed_doses(get_medication_dates(patient["therapy_start_date"], patient["dosage_schedule"]),
                                               patient.get("taken_doses"))
        })

@app.post("/doctor/edit-dosage/{patient_id}", dependencies=[Depends(get_current_user)])
async def edit_dosage(patient_id: str, dosage: List[DosageSchedule], request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        dosage_list = [i.as_dict() for i in dosage]
        collection.update_one({"type": "Patient", "ID": patient_id}, {"$set": {"dosage_schedule": dosage_list}})
        return JSONResponse(
            status_code=200,
            content={"message": "Success!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/doctor/reports", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def view_reports(typ: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    if typ == "today":
        query = {"type": "Patient"}
        results = collection.find(query)
        report_data = []
        for patient in results:
            for report in patient.get("inr_reports", []):
                if report["date"].startswith(datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")):
                    report_data.append({
                        "patient_name": patient.get("name"),
                        "inr_report": report
                    })
        return JSONResponse(
            status_code=200,
            content={"user": current_user, "reports": report_data})
    else:
        query = {"type": "Patient", "ID": typ}
        patient = collection.find_one(query)
        if patient:
            reports = [{"patient_name": patient.get("name"), "inr_report": report} for report in patient["inr_reports"]]
            html_content = templates.get_template("doctor/view_reports.html").render(
                {"request": request, "user": current_user, "reports": reports})
            html_content = html_content.replace("http://", "https://")
            return HTMLResponse(content=html_content)
        else:
            return JSONResponse(
                status_code=200,
                content={"message": "Patient not found.."})

@app.get("/patient", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def patient_home(request: Request, current_user: dict = Depends(role_required("patient"))):
    pat = current_user
    if not pat.get("inr_reports"):
        pat["inr_reports"] = [{"date": "1900-01-01T00:00", "inr_value": 0}]
    return JSONResponse(
        status_code=200,
        content={"patient": pat,
                 "chart_data": calculate_monthly_inr_average(pat.get("inr_reports")),
                 "missed_doses": find_missed_doses(get_medication_dates(pat["therapy_start_date"], pat["dosage_schedule"]),
                                                  pat.get("taken_doses"))[-1:-11:-1]})

@app.post("/patient/update-inr", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def update_inr_report(request: Request,
                            inr_value: float = Form(...),
                            location_of_test: str = Form(...),
                            date: str = Form(...),
                            file: UploadFile = File(...),
                            current_user: dict = Depends(role_required("patient"))):
    file_path = f"static/patient_docs/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    report_dict = {
        "inr_value": inr_value,
        "location_of_test": location_of_test,
        "date": date,
        "file_name": file.filename,
        "file_path": file_path,
        "type": "INR Report",
    }
    result = collection.update_one(
        {"type": "Patient", "ID": current_user["ID"]},
        {"$push": {"inr_reports": report_dict}}
    )
    if result.matched_count == 0:
        os.remove(file_path)
        raise HTTPException(status_code=404, detail="Patient not found")
    return JSONResponse(
        status_code=200,
        content={"message": "INR report added successfully", "report": report_dict})

@app.get("/patient/report", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def patient_report_form(request: Request, current_user: dict = Depends(role_required("patient"))):
    data = {
        "patient": current_user,
        "lifestyleChanges": current_user.get("lifestyleChanges"),
        "otherMedication": current_user.get("otherMedication"),
        "sideEffects": current_user.get("sideEffects"),
        "prolongedIllness": current_user.get("prolongedIllness")
    }
    return JSONResponse(status_code=200, content=data)

@app.post("/patient/report", dependencies=[Depends(get_current_user)])
async def submit_report(request: Request, typ: str = Form(None),
                        field: str = Form(None), current_user: dict = Depends(role_required("patient"))):
    collection.update_one(
        {"type": "Patient", "ID": current_user["ID"]},
        {"$push": {typ: field}}
    )
    return JSONResponse(
        status_code=200,
        content={"message": "report submitted"})

@app.get("/patient/take-dose", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def take_dose_form(request: Request, current_user: dict = Depends(role_required("patient"))):
    return JSONResponse(
        status_code=200,
        content={"patient": current_user,
                 "missed_doses": find_missed_doses(get_medication_dates(current_user["therapy_start_date"],
                                                                         current_user["dosage_schedule"]),
                                                  current_user.get("taken_doses"))})

@app.post("/patient/take-dose", dependencies=[Depends(get_current_user)])
async def take_dose(date: str, request: Request, current_user: dict = Depends(role_required("patient"))):
    collection.update_one(
        {"type": "Patient", "ID": current_user["ID"]},
        {"$push": {"taken_doses": date}}
    )
    return JSONResponse(
        status_code=200,
        content={"message": "Success!"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4502, forwarded_allow_ips="*")