from fastapi import Form, HTTPException,Depends
from fastapi.responses import JSONResponse, HTMLResponse
import hashlib
from app.utils.authutils import create_access_token,get_current_user, create_refresh_token
from app.database import patient_collection, doctor_collection
from bson import ObjectId


async def login(username: str = Form(...), password: str = Form(...)):

    if username == "admin" and password == "admin123":
        user_data = {"name": username, "role": "admin", "ID": username}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token()
        # (Optionally you may want to store the refresh token for admin as well)
        return JSONResponse(
            status_code=200,
            content={
                "message": "login successful",
                "role": "admin",
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )

    elif "DOC" in username:
        user = await doctor_collection.find_one({"ID": username})
        if user and hashlib.sha512(password.encode('utf-8')).hexdigest() == user["passHash"]:
            user2 = user.copy()
            user2.pop("passHash", None)
            if "_id" in user2:
                user2["_id"] = str(user2["_id"])
            user2.update({"role": "doctor"})
            
            access_token = create_access_token(user2)
            refresh_token = create_refresh_token()
            # Store the refresh token in the doctor document
            await doctor_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"refresh_token": refresh_token}}
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "login successful",
                    "role": "doctor",
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    elif "PAT" in username:
        pipeline = [
            {"$match": {"name": username}},
            {
                "$lookup": {
                    "from": "items",
                    "localField": "caretaker",
                    "foreignField": "ID",
                    "as": "caretaker_info"
                }
            },
            {"$unwind": {"path": "$caretaker_info", "preserveNullAndEmptyArrays": True}},  
            {"$addFields": {"caretakerName": "$caretaker_info.fullName"}}
        ]
        cursor = patient_collection.aggregate(pipeline)
        patient = await cursor.to_list(length=1)
        
        if len(patient) == 0:
            user = await patient_collection.find_one({
                "name": username,
                "caretaker": {"$exists": False}
            })
            if user and password == user["contact"].replace(" ", "").replace("+91", ""):
                user2 = user.copy()
                if "_id" in user2:
                    user2["_id"] = str(user2["_id"])
                user2.update({"role": "patient"})
                
                access_token = create_access_token(user2)
                refresh_token = create_refresh_token()
                # Store the refresh token in the patient document
                await patient_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"refresh_token": refresh_token}}
                )
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "login successful",
                        "role": "patient",
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    }
                )
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            user = patient[0]
            if password == user["contact"].replace(" ", "").replace("+91", ""):
                user2 = user.copy()
                if "_id" in user2:
                    user2["_id"] = str(user2["_id"])
                user2.update({"role": "patient"})
                
                access_token = create_access_token(user2)
                refresh_token = create_refresh_token()
                # Store the refresh token in the patient document
                await patient_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"refresh_token": refresh_token}}
                )
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "login successful",
                        "role": "patient",
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    }
                )
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


async def logout(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    user_id = current_user.get("ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found.")
    if role == "doctor":
        await doctor_collection.update_one(
            {"_id": user_id},
            {"$unset": {"refresh_token": ""}}
        )
    elif role == "patient":
        await patient_collection.update_one(
            {"_id": user_id},
            {"$unset": {"refresh_token": ""}}
        )
    elif role == "admin":
        pass
    else:
        raise HTTPException(status_code=401, detail="Invalid user role.")

    return JSONResponse(
        status_code=200,
        content={"message": "logout successful"}
    )
