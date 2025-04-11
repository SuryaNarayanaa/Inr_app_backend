from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.controllers.authController import login,logout
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.authutils import get_current_user

auth_router = APIRouter()

@auth_router.post("/login", response_class=JSONResponse)
async def login_route(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        return await login(username=form_data.username, password=form_data.password)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@auth_router.post('/logout', response_class=JSONResponse)
async def logout_route(current_user: dict = Depends(get_current_user)):
    try:
        return await logout(current_user)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})