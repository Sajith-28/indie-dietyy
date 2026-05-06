import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB URI from environment variables (or fallback for local testing)
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB."""
        if not os.getenv("MONGODB_URI"):
            print("⚠️ No MONGODB_URI provided. Running in database-free mode.")
            cls.client = None
            cls.db = None
            return

        try:
            print(f"Attempting to connect to MongoDB...")
            # Set serverSelectionTimeoutMS to quickly fail if DB is unreachable
            cls.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Trigger a ping to confirm connection
            await cls.client.admin.command('ping')
            cls.db = cls.client.indie_dietyy
            print("✅ Successfully connected to MongoDB Atlas!")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            print("Please check your .env file and MongoDB Atlas connection string.")
            cls.client = None
            cls.db = None

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client is not None:
            cls.client.close()
            print("MongoDB connection closed.")

    @classmethod
    def get_db(cls):
        return cls.db
