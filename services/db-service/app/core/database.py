from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_db_settings


class DatabaseManager:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    def connect(self, uri: str | None = None, db_name: str | None = None) -> None:
        settings = get_db_settings()
        target_uri = uri or settings.mongodb_uri
        target_db = db_name or settings.mongodb_db_name
        self.client = AsyncIOMotorClient(target_uri)
        self.db = self.client[target_db]

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    def get_database(self) -> AsyncIOMotorDatabase:
        if self.db is None:
            self.connect()
        return self.db


db_manager = DatabaseManager()


def get_db() -> AsyncIOMotorDatabase:
    return db_manager.get_database()
