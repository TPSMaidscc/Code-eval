"""
Pydantic models for the Bot Repetitions Analysis API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class RepetitionRecord(BaseModel):
    """Model for a single repetition record."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    message_id: str = Field(..., description="Unique message identifier")
    message: str = Field(..., description="The repeated message text")
    repetition_count: int = Field(..., ge=2, description="Number of times the message was repeated")
    skill: Optional[str] = Field(None, description="Bot skill that sent the message (for doctors department)")

class AnalysisSummary(BaseModel):
    """Model for analysis summary statistics."""
    conversation_id: str = Field(default="SUMMARY", description="Summary identifier")
    message_id: str = Field(default="", description="Empty for summary")
    message: str = Field(..., description="Summary message")
    repetition_count: str = Field(default="", description="Empty for summary")
    percentage_with_repetitions: str = Field(..., description="Percentage of conversations with repetitions")
    total_chats: int = Field(..., ge=0, description="Total number of conversations analyzed")
    chats_with_repetitions: int = Field(..., ge=0, description="Number of conversations with at least one repetition")

class AnalysisResult(BaseModel):
    """Model for complete analysis result."""
    department: str = Field(..., description="Department name")
    analysis_date: str = Field(..., description="Date of analysis (YYYY-MM-DD)")
    total_conversations: int = Field(..., ge=0, description="Total conversations analyzed")
    conversations_with_repetitions: int = Field(..., ge=0, description="Conversations with repetitions")
    repetition_percentage: float = Field(..., ge=0, le=100, description="Percentage of conversations with repetitions")
    repetitions: List[RepetitionRecord] = Field(default=[], description="List of repetition records")
    summary: AnalysisSummary = Field(..., description="Analysis summary statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "department": "applicants",
                "analysis_date": "2025-07-03",
                "total_conversations": 399,
                "conversations_with_repetitions": 25,
                "repetition_percentage": 6.27,
                "repetitions": [
                    {
                        "conversation_id": "conv_123",
                        "message_id": "msg_456",
                        "message": "Hello! How can I help you today?",
                        "repetition_count": 3,
                        "skill": None
                    }
                ],
                "summary": {
                    "conversation_id": "SUMMARY",
                    "message_id": "",
                    "message": "TOTAL REPETITIONS",
                    "repetition_count": "",
                    "percentage_with_repetitions": "6.27%",
                    "total_chats": 399,
                    "chats_with_repetitions": 25
                }
            }
        }

class StatusResponse(BaseModel):
    """Model for status responses."""
    status: str = Field(..., description="Status indicator")
    message: str = Field(..., description="Status message")
    department: Optional[str] = Field(None, description="Department name if applicable")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Response timestamp")

class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    department: Optional[str] = Field(None, description="Department name if applicable")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

class DepartmentInfo(BaseModel):
    """Model for department information."""
    view_name: str = Field(..., description="Tableau view name")
    skill_filter: Optional[str] = Field(None, description="Skill filter for bot messages")
    spreadsheet_id: str = Field(..., description="Google Sheets spreadsheet ID")
    output_file: str = Field(..., description="Output CSV file path")
    cleaned_file: str = Field(..., description="Cleaned data CSV file path")
    raw_data_file: str = Field(..., description="Raw data CSV file path")

class DepartmentsResponse(BaseModel):
    """Model for departments list response."""
    departments: Dict[str, DepartmentInfo] = Field(..., description="Available departments configuration")
    count: int = Field(..., description="Number of available departments")

class AnalysisRequest(BaseModel):
    """Model for analysis request parameters."""
    upload_to_sheets: bool = Field(default=True, description="Whether to upload results to Google Sheets")
    include_raw_data: bool = Field(default=False, description="Whether to include raw repetition data in response")
    date_override: Optional[str] = Field(None, description="Override analysis date (YYYY-MM-DD format)")

class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health message")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    dependencies: Dict[str, str] = Field(default={}, description="Dependency status")

class APIInfo(BaseModel):
    """Model for API information response."""
    message: str = Field(..., description="API welcome message")
    version: str = Field(..., description="API version")
    departments: List[str] = Field(..., description="Available departments")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints")
    documentation: Dict[str, str] = Field(..., description="Documentation links")
    
class BatchAnalysisResult(BaseModel):
    """Model for batch analysis results."""
    total_departments: int = Field(..., description="Total number of departments analyzed")
    successful_analyses: int = Field(..., description="Number of successful analyses")
    failed_analyses: int = Field(..., description="Number of failed analyses")
    results: List[AnalysisResult] = Field(..., description="Individual department results")
    errors: List[ErrorResponse] = Field(default=[], description="Any errors that occurred")
    summary_statistics: Dict[str, Any] = Field(..., description="Overall summary statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_departments": 4,
                "successful_analyses": 3,
                "failed_analyses": 1,
                "results": [],
                "errors": [],
                "summary_statistics": {
                    "total_conversations": 1200,
                    "total_with_repetitions": 85,
                    "overall_percentage": 7.08
                }
            }
        }
