# src/api/routes/migration.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from src.core.state import AppState, get_state
from src.data.migration import run_database_migration
from src.utils.logger import logger

router = APIRouter(prefix="/migration", tags=["Migration"])

@router.post("/fix-database", response_model=Dict[str, Any])
async def fix_database_records(
    state: AppState = Depends(get_state)
):
    """
    Fix existing database records that have missing or invalid required fields.
    This endpoint ensures all records conform to current Pydantic model requirements.
    """
    logger().info("Migration endpoint called - starting database fix")
    
    try:
        result = run_database_migration()
        
        if result['success']:
            return {
                "message": "Database migration completed successfully",
                "stats": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger().error(f"Migration endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )
