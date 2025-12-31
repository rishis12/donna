from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import get_settings
from .models_base import Base

settings = get_settings()

# Ensure DATABASE_URL uses async driver for async engine
database_url = settings.database_url
if database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
    # Convert standard postgresql:// to postgresql+asyncpg:// for async engine
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

