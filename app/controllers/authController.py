from fastapi import Form, HTTPException,Depends,Request
from fastapi.responses import JSONResponse, HTMLResponse
import hashlib
from app.utils.authutils import create_access_token,get_current_user, create_refresh_token,decode_refresh_token
from app.database import patient_collection, doctor_collection
from bson import ObjectId


async def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        user_data = {"role": "admin", "ID": username}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
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
            userdata = {"role":"doctor","ID":username}
            access_token = create_access_token(userdata)
            refresh_token = create_refresh_token(userdata)
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
    
    elif "PAT" in username:    #  review after 
        pipeline = [
            {"$match": {"ID": username}},
            {
                "$lookup": {
                    "from": "doctors",
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
                "ID": username,
                "caretaker": {"$exists": False}
            })
        else:
            user = patient[0]
        if user and password == user["contact"].replace(" ", "").replace("+91", ""):
            user2 = user.copy()
            if "_id" in user2:
                user2["_id"] = str(user2["_id"])
            
            userdata = {"role":"patient","ID":username}
            access_token = create_access_token(userdata)
            refresh_token = create_refresh_token(userdata)
            await patient_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"refresh_token": refresh_token}}
            )
                
            return JSONResponse(
                status_code=200,
                content={ "message": "login successful","role": "patient",
                        "access_token": access_token,
                        "refresh_token": refresh_token }
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


async def refresh_token(request: Request, refresh_token: str):
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e

    user_id = payload.get("ID")
    user_role = payload.get("role")
    if not user_id or not user_role:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    if user_role.lower() == "patient":
        collection = patient_collection
    elif user_role.lower() == "doctor":
        collection = doctor_collection
    else:
        raise HTTPException(status_code=401, detail="Unsupported user role")


    user = await collection.find_one({"ID": user_id})
    if not user or user.get("refresh_token") != refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token mismatch or user not found")

    new_access_token = create_access_token({"ID": user_id, "role": user_role})
    new_refresh_token = create_refresh_token({"ID": user_id, "role": user_role})

    await collection.update_one(
        {"ID": user_id},
        {"$set": {"refresh_token": new_refresh_token}}
    )

    return JSONResponse(
        status_code=200,
        content={
            "message":"Token refershed successfully",
            "role":user_role,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }
    )