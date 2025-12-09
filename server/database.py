from motor.motor_asyncio import AsyncIOMotorClient
import os

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    try:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            print("WARNING: MONGODB_URI not set, skipping database connection")
            return
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.lazydev
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")


async def close_db():
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")


def get_db():
    return db
