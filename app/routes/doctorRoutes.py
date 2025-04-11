from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse,FileResponse
from fastapi.exceptions import HTTPException
from app.controllers.doctorController import (
    doctorhome,
    get_doctors,
    reassign_doctor,
    add_patient,
    get_patients,
    view_patient,
    edit_dosage,
    view_reports,
    download_patient_report,
)
from app.utils.authutils import get_current_user, role_required

doctor_router = APIRouter()

@doctor_router.get("/",response_class = JSONResponse, dependencies=[Depends(get_current_user)])
async def home(request: Request,current_user: dict = Depends(role_required("doctor"))):
    try:
        return await doctorhome(request,current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.get("/doctors")
async def fetch_doctors(request:Request,response_class:JSONResponse):
    try:
        return await get_doctors()
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.put("/reassign/{patient_id}",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def reassign_doctor_route(
    patient_id: str,
    doc: str = Query(..., description="New Doctor or CareTakerId"),
    typ: str = Query(..., description="Doctor or CareTaker?"),
    current_user: dict = Depends(role_required("doctor")),
):
    try:
        return await reassign_doctor(patient_id, doc, typ, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.post("/add-patient",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def add_patient_route(patient_id: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        return await add_patient(patient_id, request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.get("/patients",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def fetch_patients(request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        return await get_patients(request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.get("/view-patient/{patient_id}",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def fetch_patient(patient_id: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        return await view_patient(patient_id, request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.put("/edit-dosage/{patient_id}",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def edit_dosage_route(
    patient_id: str, dosage: list, request: Request, current_user: dict = Depends(role_required("doctor"))
):
    try:
        return await edit_dosage(patient_id, dosage, request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.get("/reports",response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def fetch_reports(typ: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        return await view_reports(typ, request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@doctor_router.get("/download-report/{patient_id}",response_class=FileResponse, dependencies=[Depends(get_current_user)])
async def download_report(patient_id: str, request: Request, current_user: dict = Depends(role_required("doctor"))):
    try:
        return await download_patient_report(patient_id, request, current_user)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})