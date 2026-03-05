import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Load env
import sys
sys.path.insert(0, "/absolute/path/backend")

from app.models.lead import Lead
from app.core.config import settings

async def check_leads():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(Lead))
        leads = result.scalars().all()
        
        if leads:
            for lead in leads[:5]:  # First 5
                print(f"Lead ID: {lead.id}")
                print(f"  Campaign ID: {lead.campaign_id}")
                print(f"  Phone: '{lead.phone}'")
                print(f"  Status: {lead.status}")
                print()
        else:
            print("No leads found!")

asyncio.run(check_leads())
