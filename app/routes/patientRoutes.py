from fastapi import APIRouter,Depends,Request,HTTPException,File,Form,UploadFile,Query,Body
from fastapi.responses import JSONResponse
from app.utils.authutils import get_current_user,role_required
from app.controllers.patientController import ( patient_home,update_inr_report,
        patient_reports,submit_report,get_missed_doses,take_dose )
from app.schema.patientSchema import DoseInput

patient_router = APIRouter()

@patient_router.get("/",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def get_patients(request: Request,current_user: dict = Depends(role_required("patient"))):
    try:
        return await patient_home(request,current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@patient_router.post("/update-inr",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def update_inr(request: Request,
    inr_value: float = Form(...),
    location_of_test: str = Form(...),
    date: str = Form(...),
    file: str = Form(None),
    file_name:str = Form(None),
    current_user: dict = Depends(role_required("patient"))):
    try:
        return await update_inr_report(request,inr_value,location_of_test,date,file,file_name,current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@patient_router.get("/report",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def get_report(request: Request,current_user: dict = Depends(role_required("patient"))):
    try:
        return await patient_reports(request,current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@patient_router.post("/report",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def post_report(request: Request,
    typ: str = Query(..., description="type of report to change"),
    field: str = Form(...), 
    current_user: dict = Depends(role_required("patient"))):
    try:
        return await submit_report(request,typ,field,current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@patient_router.get("/missedDoses",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def misses_doses(request: Request,current_user: dict = Depends(role_required("patient"))):
    try:
        return await get_missed_doses(request,current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@patient_router.put("/take_dose",response_class=JSONResponse,dependencies=[Depends(get_current_user)])
async def put_taken_dose(request: Request, dose_input: DoseInput = Body(...), current_user: dict = Depends(role_required("patient"))):
    try:
        return await take_dose(request, dose_input.date, current_user)
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})    