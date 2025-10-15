
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "resume_screener")

_client = AsyncIOMotorClient(MONGODB_URI)
db = _client[MONGO_DB]

# helper accessors
def get_collection(name="resumes"):
    return db[name]
