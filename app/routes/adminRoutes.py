from fastapi import APIRouter,Depends,Request
from fastapi.responses import JSONResponse
from app.controllers.adminController import getadmindetails,create_patient,create_doctor,patient_modify,doctor_modify
from app.utils.authutils import get_current_user, role_required

admin_router = APIRouter()

@admin_router.get("/", response_model=dict, dependencies=[Depends(role_required("admin"))])
async def get_admin_details(current_user: dict = Depends(get_current_user)):
    try:
        return await getadmindetails(current_user)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    
@admin_router.post("/add_patient",response_class=JSONResponse, dependencies=[Depends(role_required("admin"))])
async def add_patient(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        patient_data = await request.json()
        print(patient_data)
        result = await create_patient(patient_data)
        return JSONResponse(status_code=201, content={"message": "Patient added successfully", "patient_id": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    
@admin_router.post('/add_doctor',response_class=JSONResponse, dependencies=[Depends(role_required("admin"))])
async def add_doctor(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        doctor_data = await request.json()
        result = await create_doctor(doctor_data)
        return JSONResponse(status_code=201, content={"message": "Doctor added successfully", "doctor_id": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@admin_router.put("/modify_doctor/{doctor_id}", response_class=JSONResponse, dependencies=[Depends(role_required("admin"))])
async def modify_doctor(doctor_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        doctor_data = await request.json()
        result = await doctor_modify(doctor_id, doctor_data, current_user)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


@admin_router.put("/modify_patient/{patient_id}", response_class=JSONResponse, dependencies=[Depends(role_required("admin"))])
async def modify_patient(patient_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        patient_data = await request.json()
        result = await patient_modify(patient_id, patient_data, current_user)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})