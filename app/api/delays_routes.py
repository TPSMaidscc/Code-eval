"""
API routes for delays analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.delays_service import DelaysAnalysisService
from app.config import DEPARTMENT_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delays", tags=["delays"])

@router.post("/analyze/{department}")
async def analyze_department_delays(
    department: str,
    upload_to_sheets: bool = Query(True, description="Upload results to Google Sheets"),
    date_override: Optional[str] = Query(None, description="Override analysis date (YYYY-MM-DD)")
):
    """
    Analyze response time delays for a specific department.
    
    Args:
        department: Department name (doctors, cc_sales, applicants, mv_resolvers)
        upload_to_sheets: Whether to upload results to Google Sheets
        date_override: Override analysis date (YYYY-MM-DD), defaults to yesterday
    
    Returns:
        Analysis results with response time statistics
    """
    if department not in DEPARTMENT_CONFIG:
        available_departments = list(DEPARTMENT_CONFIG.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid department '{department}'. Available departments: {available_departments}"
        )
    
    try:
        logger.info(f"Starting delays analysis for department: {department}")
        
        delays_service = DelaysAnalysisService()
        result = await delays_service.analyze_department_delays(
            department=department,
            upload_to_sheets=upload_to_sheets,
            date_override=date_override
        )
        
        logger.info(f"Completed delays analysis for department: {department}")
        return result
        
    except Exception as e:
        logger.error(f"Delays analysis failed for {department}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Delays analysis failed for {department}: {str(e)}"
        )

@router.get("/departments")
async def get_available_departments():
    """Get list of available departments for delays analysis."""
    departments = []
    for dept_name, config in DEPARTMENT_CONFIG.items():
        departments.append({
            "name": dept_name,
            "view_name": config["view_name"],
            "skill_filter": config["skill_filter"]
        })
    
    return {
        "departments": departments,
        "total": len(departments)
    }

@router.get("/health")
async def delays_health_check():
    """Health check for delays analysis service."""
    try:
        # Test service initialization
        delays_service = DelaysAnalysisService()
        
        return {
            "status": "healthy",
            "service": "delays_analysis",
            "available_departments": list(DEPARTMENT_CONFIG.keys())
        }
    except Exception as e:
        logger.error(f"Delays service health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Delays service health check failed: {str(e)}"
        )
