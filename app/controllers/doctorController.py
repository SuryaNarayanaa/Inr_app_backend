from fastapi import  Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from utils.authutils import role_required
from database import patient_collection,doctor_collection

async def doctorhome(request:Request,current_user:dict = Depends(role_required("doctor"))):
    pipeline = [
        {"$match": {"doctor": current_user["ID"]}},
        {"$lookup": {
            "from": "doctor",
            "localField": "caretaker",
            "foreignField": "ID",
            "as": "caretaker_info"
        }},
        {"$unwind": "$caretaker_info"},
        {"$addFields": {"caretakerName": "$caretaker_info.fullName"}},
        {"$project": {"caretakerName": 1, "name": 1, "doctor": 1, "ID": 1, "age": 1, "gender": 1}}
    ]