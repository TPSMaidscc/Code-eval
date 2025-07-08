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
from app.services.delays_service import DelaysAnalysisService
from app.api.delays_routes import router as delays_router

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Include delays routes
router.include_router(delays_router)

# Initialize analysis services
analysis_service = RepetitionsAnalysisService()
delays_service = DelaysAnalysisService()

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
        # Check if agent percentage function exists (version check)
        try:
            from app.services.delays_service import DelaysService
            delays_service_instance = DelaysService()
            has_agent_percentage = hasattr(delays_service_instance, 'calculate_agent_percentage')
        except:
            has_agent_percentage = False

        # Basic health checks
        dependencies = {
            "tableau_service": "healthy",
            "sheets_service": "healthy",
            "analysis_service": "healthy",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "agent_percentage_feature": "available" if has_agent_percentage else "missing"
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

# Combined Analysis Endpoints
@router.post("/analyze/combined/{department}")
async def analyze_combined(
    department: str,
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """
    Run both repetitions and delays analysis for a department in a single call.

    This endpoint combines both analyses:
    - Repetitions analysis (finds repeated bot messages)
    - Delays analysis (calculates bot response times)

    Args:
        department: Department name (applicants, doctors, cc_sales, mv_resolvers)
        upload_to_sheets: Whether to upload results to Google Sheets
        date_override: Specific date to analyze (YYYY-MM-DD format), defaults to yesterday

    Returns:
        Combined results from both analyses
    """
    logger.info(f"Starting combined analysis for {department}")

    # Validate department
    if department not in DEPARTMENT_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Department '{department}' not found. Available: {list(DEPARTMENT_CONFIG.keys())}"
        )

    try:
        # Get department configuration
        config = DEPARTMENT_CONFIG[department]

        # Determine analysis date
        from datetime import datetime, timedelta
        if date_override:
            analysis_date = date_override
        else:
            yesterday = datetime.now() - timedelta(days=1)
            analysis_date = yesterday.strftime("%Y-%m-%d")

        logger.info(f"Fetching data once for both analyses - Date: {analysis_date}")

        # Fetch data from Tableau once
        from app.services.tableau_service import TableauService
        import pandas as pd
        import os

        tableau_service = TableauService()
        raw_data_file = config['raw_data_file']

        # Ensure data directory exists
        os.makedirs(os.path.dirname(raw_data_file), exist_ok=True)

        # Fetch data for the analysis date
        start_date = analysis_date
        end_date = analysis_date

        logger.info(f"Fetching data from Tableau view: {config['view_name']}")
        if not tableau_service.fetch_data(config['view_name'], raw_data_file, start_date, end_date):
            raise RuntimeError(f"Failed to fetch data from Tableau for {department}")

        # Load the data once
        logger.info(f"Loading data from {raw_data_file}")
        df = pd.read_csv(raw_data_file)

        if df.empty:
            logger.warning(f"No data found for {department} on {analysis_date}")
            return {
                "department": department,
                "analysis_date": analysis_date,
                "status": "NO_DATA",
                "repetitions_analysis": {"status": "NO_DATA", "message": "No data found"},
                "delays_analysis": {"status": "NO_DATA", "message": "No data found"},
                "message": "No data found for the specified date"
            }

        logger.info(f"Loaded {len(df)} rows of data for combined analysis")

        # Run repetitions analysis with pre-loaded data
        logger.info(f"Running repetitions analysis for {department}")
        repetitions_result = await analysis_service.analyze_department_with_data(
            department=department,
            df=df.copy(),  # Use a copy to avoid modifying original data
            analysis_date=analysis_date,
            upload_to_sheets=upload_to_sheets
        )

        # Run delays analysis using the same working method as individual endpoint
        logger.info(f"Running delays analysis for {department}")
        delays_result = await delays_service.analyze_department_delays(
            department=department,
            df=df.copy(),  
            upload_to_sheets=upload_to_sheets,
            date_override=analysis_date
        )

        # Combine results
        # repetitions_result is an AnalysisResult object
        # delays_result is a dictionary

        # Create summary data for the summary sheet
        summary_data = {}

        # Get total conversations from data_counts
        data_counts = delays_result.get("data_counts", {})
        summary_data['total_conversations'] = data_counts.get('total_conversations', '')

        # Get repetition percentage - format as "count (percentage%)"
        chats_with_reps = repetitions_result.conversations_with_repetitions
        repetition_percentage = repetitions_result.repetition_percentage
        summary_data['repetition_percentage'] = f" {repetition_percentage:.2f}%({chats_with_reps})"

        # Get delays analysis summary
        delays_summary = delays_result.get("summary", {})
        first_response = delays_summary.get("first_response", {})
        subsequent_response = delays_summary.get("subsequent_response", {})

        # Use formatted response times (MM:SS with count over 4 min)
        summary_data['avg_delay_initial'] = first_response.get('avg_response_time_formatted', first_response.get('avg_response_time', ''))
        summary_data['avg_delay_subsequent'] = subsequent_response.get('avg_response_time_formatted', subsequent_response.get('avg_response_time', ''))

        # Get agent intervention percentage
        agent_intervention = delays_summary.get("agent_intervention", {})
        summary_data['agent_intervention_percentage'] = agent_intervention.get('formatted', agent_intervention.get('percentage', ''))

        # Get handling percentage
        handling = delays_summary.get("handling", {})
        summary_data['handling_percentage'] = handling.get('formatted', handling.get('percentage', ''))

        # Upload to summary sheet if requested
        if upload_to_sheets:
            try:
                from app.config import SUMMARY_SPREADSHEET_IDS
                from app.services.sheets_service import get_sheets_service

                summary_spreadsheet_id = SUMMARY_SPREADSHEET_IDS.get(department)
                if summary_spreadsheet_id:
                    sheets_service = get_sheets_service()
                    sheet_name = repetitions_result.analysis_date  # Format: YYYY-MM-DD

                    success = sheets_service.create_summary_sheet(
                        summary_spreadsheet_id, sheet_name, summary_data
                    )

                    if success:
                        logger.info(f"Successfully created summary sheet for {department}")
                    else:
                        logger.warning(f"Failed to create summary sheet for {department}")
                else:
                    logger.warning(f"No summary spreadsheet ID configured for {department}")

            except Exception as e:
                logger.warning(f"Failed to create summary sheet for {department}: {e}")

        combined_result = {
            "department": department,
            "analysis_date": repetitions_result.analysis_date,
            "status": "SUCCESS",
            "repetitions_analysis": {
                "status": "SUCCESS",
                "summary": repetitions_result.summary,
                "total_conversations": repetitions_result.total_conversations,
                "conversations_with_repetitions": repetitions_result.conversations_with_repetitions,
                "repetition_percentage": repetitions_result.repetition_percentage,
                "repetitions_count": len(repetitions_result.repetitions)
            },
            "delays_analysis": {
                "status": delays_result.get("status"),
                "summary": delays_result.get("summary", {}),
                "files": delays_result.get("files", {}),
                "data_counts": delays_result.get("data_counts", {})
            },
            "summary_sheet": {
                "created": upload_to_sheets,
                "data": summary_data
            },
            "message": f"Combined analysis completed for {department}"
        }

        logger.info(f"Combined analysis completed successfully for {department}")
        return combined_result

    except Exception as e:
        logger.error(f"Combined analysis failed for {department}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Combined analysis failed: {str(e)}")

# Individual combined endpoints for each department
@router.post("/analyze/combined/applicants")
async def analyze_combined_applicants(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Run both repetitions and delays analysis for Applicants department."""
    return await analyze_combined("applicants", upload_to_sheets, date_override)

@router.post("/analyze/combined/doctors")
async def analyze_combined_doctors(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Run both repetitions and delays analysis for Doctors department."""
    return await analyze_combined("doctors", upload_to_sheets, date_override)

@router.post("/analyze/combined/mv_resolvers")
async def analyze_combined_mv_resolvers(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Run both repetitions and delays analysis for MV Resolvers department."""
    return await analyze_combined("mv_resolvers", upload_to_sheets, date_override)

@router.post("/analyze/combined/cc_sales")
async def analyze_combined_cc_sales(
    upload_to_sheets: bool = Query(default=True),
    date_override: Optional[str] = Query(default=None)
):
    """Run both repetitions and delays analysis for CC Sales department."""
    return await analyze_combined("cc_sales", upload_to_sheets, date_override)
