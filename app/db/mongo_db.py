from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_mongo = MongoDB()

async def connect_to_mongo():
    db_mongo.client = AsyncIOMotorClient(settings.MONGO_URL)
    db_mongo.db = db_mongo.client[settings.MONGO_DB_NAME]
    print("Conectado a MongoDB")

async def close_mongo_connection():
    if db_mongo.client:
        db_mongo.client.close()
        print("Conexión a MongoDB cerrada")

# Dependencia para FastAPI
async def get_mongo():
    return db_mongo.db