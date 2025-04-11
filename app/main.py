from fastapi import FastAPI
import uvicorn
from app.database import MongoDB
from app.routes.authRoutes import auth_router
from app.routes.adminRoutes import admin_router

app = FastAPI()

@app.get("/")
async def heath_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    await MongoDB.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await MongoDB.disconnect()

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router,prefix='/admin',tags=['Admin'])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", reload=True)