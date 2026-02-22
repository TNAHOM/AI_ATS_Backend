import logging
import traceback
from contextlib import asynccontextmanager
from typing import Type, Any
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.common import ProcessingStatus

logger = logging.getLogger(__name__)

@asynccontextmanager
async def task_monitor(model_class: Type[Any], entity_id: Any):
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
            
            # 4. Success Case
            # We refresh to make sure we don't overwrite any changes made inside the worker
            await session.refresh(entity) 
            entity.processing_status = ProcessingStatus.COMPLETED
            session.add(entity)
            await session.commit()
            logger.info(f"Task for {model_class.__name__} {entity_id} completed successfully.")

        except Exception as e:
            # 5. Failure Case
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Task for {model_class.__name__} {entity_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            
            # Save error to DB so frontend can see it
            entity.processing_status = ProcessingStatus.FAILED
            entity.processing_error = error_msg
            session.add(entity)
            await session.commit()