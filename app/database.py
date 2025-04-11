# app/database.py

import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DB_URL = os.environ.get("MONGO_DB_URL", "mongodb+srv://karthick:karthick@nodejs.ntg4omj.mongodb.net/inr")

class MongoDB:
    client: AsyncIOMotorClient = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(MONGO_DB_URL)
        logging.info("Connected to MongoDB.")

    @classmethod
    def get_database(cls, db_name: str):
        if cls.client is None:
            raise Exception("Database connection not established. Call MongoDB.connect() first.")
        return cls.client[db_name]

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            logging.info("MongoDB connection closed.")


client = AsyncIOMotorClient(MONGO_DB_URL)
db = client.get_database('inr')

patient_collection = db["patients"]
doctor_collection = db["doctors"]
