import logging
import traceback
from contextlib import asynccontextmanager
from typing import Type, Any
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.common import ProcessingStatus
from typing import AsyncGenerator, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@asynccontextmanager
async def task_monitor(model_class: Type[Any], entity_id: Any) -> AsyncGenerator[Tuple[Optional[Any], Optional[AsyncSession]], None]:
    """
    A context manager that:
    1. Opens a DB session.
    2. Fetches the entity.
    3. Sets status to PROCESSING.
    4. Yields the entity and session to the worker logic.
    5. On Success: Sets status to COMPLETED.
    6. On Error: Sets status to FAILED and saves the error message.
    """
    async with async_session_maker() as session:
        # 1. Fetch Entity
        result = await session.execute(select(model_class).where(model_class.id == entity_id))
        entity = result.scalar_one_or_none()
        
        if not entity:
            logger.error(f"{model_class.__name__} {entity_id} not found in worker.")
            yield None, None # Skip execution
            return

        # 2. Set Processing
        entity.processing_status = ProcessingStatus.PROCESSING
        entity.processing_error = None
        session.add(entity)
        await session.commit()
        
        try:
            # 3. YIELD control back to the specific worker function
            yield entity, session
            
            # await session.refresh(entity) 
            entity.processing_status = ProcessingStatus.COMPLETED
            session.add(entity)
            await session.commit()
            logger.info(f"Task for {model_class.__name__} {entity_id} completed successfully.")

        except Exception as e:
            # 5. Failure Case
            # Here we DO refresh or rollback to ensure we have a clean state to write the error
            await session.rollback() 
            # Re-fetch is safer after rollback to attach to current session
            entity.processing_status = ProcessingStatus.FAILED
            entity.processing_error = f"{type(e).__name__}: {str(e)}"
            session.add(entity)
            await session.commit()
            
            logger.error(f"Task failed: {str(e)}")
            logger.error(traceback.format_exc())