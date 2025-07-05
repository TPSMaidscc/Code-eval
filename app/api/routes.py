"""
API routes for the Bot Repetitions Analysis API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import os

from app.models import (
    AnalysisResult, StatusResponse, DepartmentsResponse, DepartmentInfo,
    APIInfo, HealthResponse, BatchAnalysisResult, ErrorResponse
)
from app.config import DEPARTMENT_CONFIG, API_VERSION
from app.services.analysis_service import RepetitionsAnalysisService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize analysis service
analysis_service = RepetitionsAnalysisService()

@router.get("/", response_model=APIInfo)
async def root():
    """Root endpoint with API information."""
    return APIInfo(
        message="Bot Repetitions Analysis API",
        version=API_VERSION,
        departments=list(DEPARTMENT_CONFIG.keys()),
        endpoints={
            "analyze_all": "/analyze/all",
            "analyze_applicants": "/analyze/applicants",
            "analyze_doctors": "/analyze/doctors", 
            "analyze_mv_resolvers": "/analyze/mv_resolvers",
            "analyze_cc_sales": "/analyze/cc_sales",
            "health": "/health",
            "departments": "/departments"
        },
        documentation={
            "interactive_docs": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        }
    )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Basic health checks
        dependencies = {
            "tableau_service": "healthy",
            "sheets_service": "healthy",
            "analysis_service": "healthy",
            "environment": os.getenv("ENVIRONMENT", "development")
        }

        return HealthResponse(
            status="healthy",
            message="Bot Repetitions Analysis API is running",
            version=API_VERSION,
            dependencies=dependencies
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@router.get("/departments", response_model=DepartmentsResponse)
async def get_departments():
    """Get list of available departments and their configuration."""
    departments = {}
    for dept_name, config in DEPARTMENT_CONFIG.items():
        departments[dept_name] = DepartmentInfo(**config)
    
    return DepartmentsResponse(
        departments=departments,
        count=len(departments)
    )

@router.post("/analyze/{department}", response_model=AnalysisResult)
async def analyze_department_endpoint(
    department: str,
    upload_to_sheets: bool = Query(default=True, description="Whether to upload results to Google Sheets"),
    date_override: Optional[str] = Query(default=None, description="Override analysis date (YYYY-MM-DD)")
):
    """Analyze repetitions for a specific department."""
    if department not in DEPARTMENT_CONFIG:
        available_departments = list(DEPARTMENT_CONFIG.keys())
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown department: {department}. Available: {available_departments}"
        )
    
    try:
        logger.info(f"Starting analysis for department: {department}")
        result = await analysis_service.analyze_department(
            department, 
            upload_to_sheets=upload_to_sheets,
            date_override=date_override
        )
        logger.info(f"Completed analysis for department: {department}")
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed for {department}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis failed for {department}: {str(e)}"
        )

@router.post("/analyze/all", response_model=BatchAnalysisResult)
async def analyze_all_departments(
    upload_to_sheets: bool = Query(default=True, description="Whether to upload results to Google Sheets"),
    date_override: Optional[str] = Query(default=None, description="Override analysis date (YYYY-MM-DD)")
):
    """Analyze repetitions for all departments."""
    logger.info("Starting analysis for all departments")
    
    results = []
    errors = []
    successful_analyses = 0
    failed_analyses = 0
    
    for department in DEPARTMENT_CONFIG.keys():
        try:
            logger.info(f"Analyzing department: {department}")
            result = await analysis_service.analyze_department(
                department, 
                upload_to_sheets=upload_to_sheets,
                date_override=date_override
            )
            results.append(result)
            successful_analyses += 1
            logger.info(f"Completed analysis for {department}")
            
        except Exception as e:
            error_msg = f"Failed to analyze {department}: {str(e)}"
            logger.error(error_msg)
            
            error_response = ErrorResponse(
                error="AnalysisError",
                message=error_msg,
                department=department,
                detail=str(e)
            )
            errors.append(error_response)
            failed_analyses += 1
    
    # Calculate summary statistics
    if results:
        total_conversations = sum(r.total_conversations for r in results)
        total_with_reps = sum(r.conversations_with_repetitions for r in results)
        overall_percentage = (total_with_reps / total_conversations * 100) if total_conversations > 0 else 0
        
        summary_statistics = {
            "total_conversations": total_conversations,
            "total_with_repetitions": total_with_reps,
            "overall_percentage": round(overall_percentage, 2),
            "department_breakdown": {
                r.department: {
                    "percentage": r.repetition_percentage,
                    "conversations": r.total_conversations,
                    "with_repetitions": r.conversations_with_repetitions
                } for r in results
            }
        }
    else:
        summary_statistics = {
            "total_conversations": 0,
            "total_with_repetitions": 0,
            "overall_percentage": 0.0,
            "department_breakdown": {}
        }
    
    # If all analyses failed, return error
    if failed_analyses > 0 and successful_analyses == 0:
        raise HTTPException(
            status_code=500, 
            detail=f"All analyses failed. Errors: {[e.message for e in errors]}"
        )
    
    batch_result = BatchAnalysisResult(
        total_departments=len(DEPARTMENT_CONFIG),
        successful_analyses=successful_analyses,
        failed_analyses=failed_analyses,
        results=results,
        errors=errors,
        summary_statistics=summary_statistics
    )
    
    logger.info(f"Completed batch analysis: {successful_analyses} successful, {failed_analyses} failed")
    return batch_result

# Individual department endpoints for convenience
@router.post("/analyze/applicants", response_model=AnalysisResult)
async def analyze_applicants(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Analyze repetitions for Applicants department."""
    return await analyze_department_endpoint("applicants", upload_to_sheets, date_override)

@router.post("/analyze/doctors", response_model=AnalysisResult)
async def analyze_doctors(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Analyze repetitions for Doctors department."""
    return await analyze_department_endpoint("doctors", upload_to_sheets, date_override)

@router.post("/analyze/mv_resolvers", response_model=AnalysisResult)
async def analyze_mv_resolvers(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Analyze repetitions for MV Resolvers department."""
    return await analyze_department_endpoint("mv_resolvers", upload_to_sheets, date_override)

@router.post("/analyze/cc_sales", response_model=AnalysisResult)
async def analyze_cc_sales(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Analyze repetitions for CC Sales department."""
    return await analyze_department_endpoint("cc_sales", upload_to_sheets, date_override)
