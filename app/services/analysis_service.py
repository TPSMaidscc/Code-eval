"""
Repetitions analysis service
"""

import pandas as pd
import logging
import os
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.config import DEPARTMENT_CONFIG
from app.models import RepetitionRecord, AnalysisSummary, AnalysisResult
from app.services.tableau_service import TableauService
from app.services.sheets_service import get_sheets_service

logger = logging.getLogger(__name__)

class RepetitionsAnalysisService:
    """Service for analyzing bot message repetitions."""
    
    def __init__(self):
        self.tableau_service = TableauService()
    
    def preprocess_data(self, df: pd.DataFrame, department: str) -> pd.DataFrame:
        """Preprocess conversation data."""
        logger.info(f"Preprocessing data for {department}")
        
        df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'])
        # Sort by conversation id and message sent time
        df = df.sort_values(by=['Conversation ID', 'Message Sent Time'])
        
        # Drop duplicates
        original_count = len(df)
        df = df.drop_duplicates(subset=['Conversation ID', 'Message Sent Time'], keep='first')
        duplicates_removed = original_count - len(df)
        
        # Save cleaned data
        config = DEPARTMENT_CONFIG[department]
        df.to_csv(config['cleaned_file'], index=False)
        
        logger.info(f"Preprocessed {len(df)} records for {department} (removed {duplicates_removed} duplicates)")
        return df
    
    def get_repetitions(self, df: pd.DataFrame, department: str) -> Tuple[List[Dict[str, Any]], float, int, int]:
        """Analyze repetitions in conversation data."""
        logger.info(f"Analyzing repetitions for {department}")
        
        config = DEPARTMENT_CONFIG[department]
        repetition_data = []
        chats_with_repetition = set()
        
        # Process each conversation
        for conversation_id in df['Conversation ID'].unique():
            conversation_df = df[df['Conversation ID'] == conversation_id]
            
            # Filter bot messages based on department
            if config['skill_filter']:
                skill_filters = config['skill_filter']
                if isinstance(skill_filters, str):
                    # Handle backward compatibility with single string
                    skill_filters = [skill_filters]

                # Create a pattern that matches any of the skill filters
                skill_pattern = '|'.join(skill_filters)
                bot_messages = conversation_df[
                    (conversation_df['Sent By'].str.lower() == 'bot') &
                    (conversation_df['Message Type'].str.lower() == 'normal message') &
                    (conversation_df['Skill'].str.contains(skill_pattern, na=False, case=False))
                ]
            else:
                # CC Sales - all bot messages
                bot_messages = conversation_df[
                    (conversation_df['Sent By'].str.lower() == 'bot') &
                    (conversation_df['Message Type'].str.lower() == 'normal message')
                ]
            
            if bot_messages.empty:
                continue
            
            # Count message occurrences
            message_counts = bot_messages['TEXT'].value_counts()
            repeated_messages = message_counts[message_counts > 1]
            
            # Store repetition data
            for message, count in repeated_messages.items():
                first_occurrence = bot_messages[bot_messages['TEXT'] == message].iloc[0]
                repetition_record = {
                    'conversation_id': conversation_id,
                    'message_id': first_occurrence.get('MESSAGE_ID', ''),
                    'message': message,
                    'repetition_count': int(count)
                }
                
                # Add skill for doctors department
                if department == 'doctors':
                    repetition_record['skill'] = first_occurrence.get('Skill', '')
                
                repetition_data.append(repetition_record)
                chats_with_repetition.add(conversation_id)
        
        # Calculate statistics
        total_chats = 0
        for conversation_id in df['Conversation ID'].unique():
            conversation_df = df[df['Conversation ID'] == conversation_id]
            if config['skill_filter']:
                skill_filters = config['skill_filter']
                if isinstance(skill_filters, str):
                    # Handle backward compatibility with single string
                    skill_filters = [skill_filters]

                # Create a pattern that matches any of the skill filters
                skill_pattern = '|'.join(skill_filters)
                if conversation_df['Skill'].str.contains(skill_pattern, case=False, na=False).any():
                    total_chats += 1
            else:
                # CC Sales - count all conversations
                total_chats += 1
        
        chats_with_reps = len(chats_with_repetition)
        percentage = (chats_with_reps / total_chats) * 100 if total_chats > 0 else 0
        
        logger.info(f"Found {len(repetition_data)} repetitions in {chats_with_reps}/{total_chats} conversations ({percentage:.2f}%)")
        
        return repetition_data, percentage, chats_with_reps, total_chats
    
    def save_results(self, repetition_data: List[Dict[str, Any]], department: str, 
                    percentage: float, chats_with_reps: int, total_chats: int) -> str:
        """Save analysis results to CSV file."""
        config = DEPARTMENT_CONFIG[department]
        
        # Create repetitions DataFrame
        if repetition_data:
            repetitions_df = pd.DataFrame(repetition_data)
        else:
            repetitions_df = pd.DataFrame()
        
        # Add summary row
        summary_data = {
            'conversation_id': 'SUMMARY',
            'message_id': '',
            'message': 'TOTAL REPETITIONS' if repetition_data else 'NO REPETITIONS FOUND',
            'repetition_count': '',
            'percentage_with_repetitions': f"{percentage:.2f}%",
            'total_chats': total_chats,
            'chats_with_repetitions': chats_with_reps
        }
        
        # Combine data and summary
        if not repetitions_df.empty:
            summary_row = pd.DataFrame([summary_data])
            final_df = pd.concat([repetitions_df, summary_row], ignore_index=True)
        else:
            final_df = pd.DataFrame([summary_data])
        
        # Save to CSV
        output_file = config['output_file']
        final_df.to_csv(output_file, index=False)
        
        logger.info(f"Results saved to {output_file}")
        return output_file
    
    async def analyze_department(self, department: str, upload_to_sheets: bool = True, 
                               date_override: Optional[str] = None) -> AnalysisResult:
        """
        Analyze repetitions for a specific department.
        
        Args:
            department: Department name
            upload_to_sheets: Whether to upload results to Google Sheets
            date_override: Override analysis date (YYYY-MM-DD)
        
        Returns:
            AnalysisResult with analysis data
        """
        if department not in DEPARTMENT_CONFIG:
            raise ValueError(f"Unknown department: {department}")
        
        config = DEPARTMENT_CONFIG[department]
        
        try:
            # Fetch data from Tableau
            logger.info(f"Fetching data for {department} from Tableau")
            
            # Determine date range
            if date_override:
                start_date = end_date = date_override
                analysis_date = date_override
            else:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = end_date = yesterday.strftime("%Y-%m-%d")
                analysis_date = start_date
            
            # Fetch data
            if not self.tableau_service.fetch_data(config['view_name'], config['raw_data_file'], 
                                                 start_date, end_date):
                raise RuntimeError(f"Failed to fetch data from Tableau for {department}")
            
            # Load and preprocess data
            df = pd.read_csv(config['raw_data_file'])
            if df.empty:
                logger.warning(f"No data found for {department} on {analysis_date}")
                # Return empty result
                return AnalysisResult(
                    department=department,
                    analysis_date=analysis_date,
                    total_conversations=0,
                    conversations_with_repetitions=0,
                    repetition_percentage=0.0,
                    repetitions=[],
                    summary=AnalysisSummary(
                        message="NO DATA FOUND",
                        percentage_with_repetitions="0.00%",
                        total_chats=0,
                        chats_with_repetitions=0
                    )
                )
            
            df = self.preprocess_data(df, department)
            
            # Analyze repetitions
            repetition_data, percentage, chats_with_reps, total_chats = self.get_repetitions(df, department)
            
            # Save results
            output_file = self.save_results(repetition_data, department, percentage, chats_with_reps, total_chats)
            
            # Upload to Google Sheets if requested
            if upload_to_sheets:
                try:
                    sheet_name = "Repetitions " + (datetime.now() - timedelta(days=1)).strftime("%B %d")
                    # Use Service Account authentication
                    sheets_service = get_sheets_service()

                    success = sheets_service.upload_csv_to_sheet(
                        config['spreadsheet_id'],
                        output_file,
                        sheet_name
                    )
                    
                    if success:
                        logger.info(f"Successfully uploaded {department} data to Google Sheets")
                    else:
                        logger.warning(f"Failed to upload {department} data to Google Sheets")
                        
                except Exception as e:
                    logger.warning(f"Failed to upload to Google Sheets for {department}: {e}")
            
            # Prepare API response
            repetitions = [RepetitionRecord(**record) for record in repetition_data]
            
            summary = AnalysisSummary(
                message='TOTAL REPETITIONS' if repetition_data else 'NO REPETITIONS FOUND',
                percentage_with_repetitions=f"{percentage:.2f}%",
                total_chats=total_chats,
                chats_with_repetitions=chats_with_reps
            )
            
            result = AnalysisResult(
                department=department,
                analysis_date=analysis_date,
                total_conversations=total_chats,
                conversations_with_repetitions=chats_with_reps,
                repetition_percentage=round(percentage, 2),
                repetitions=repetitions,
                summary=summary
            )

            return result

        except Exception as e:
            logger.error(f"Analysis failed for {department}: {str(e)}")
            raise RuntimeError(f"Analysis failed for {department}: {str(e)}")

    async def analyze_department_with_data(self, department: str, df: pd.DataFrame,
                                         analysis_date: str, upload_to_sheets: bool = True) -> AnalysisResult:
        """
        Analyze repetitions for a department using pre-loaded data.

        This method is optimized for combined analysis where data is already fetched.

        Args:
            department: Department name
            df: Pre-loaded DataFrame with conversation data
            analysis_date: Date of analysis (YYYY-MM-DD format)
            upload_to_sheets: Whether to upload results to Google Sheets

        Returns:
            AnalysisResult with analysis results
        """
        logger.info(f"Starting repetitions analysis for {department} with pre-loaded data")

        try:
            # Get department configuration
            config = DEPARTMENT_CONFIG[department]
            skill_filter = config['skill_filter']

            logger.info(f"Processing {len(df)} rows for {department} with skill filters: {skill_filter}")

            # Preprocess the data
            preprocessed_df = self.preprocess_data(df, department)

            # Get repetitions analysis
            repetition_data, percentage, chats_with_reps, total_chats = self.get_repetitions(preprocessed_df, department)

            if not repetition_data:
                logger.warning(f"No repetitions found for {department} with skill filters {skill_filter}")
                # Create empty summary
                skill_filter_str = ', '.join(skill_filter) if isinstance(skill_filter, list) else str(skill_filter)
                summary = AnalysisSummary(
                    message=f'NO REPETITIONS FOUND for {skill_filter_str}',
                    percentage_with_repetitions="0.00%",
                    total_chats=total_chats,
                    chats_with_repetitions=0
                )
                # Return AnalysisResult object for consistency
                return AnalysisResult(
                    department=department,
                    analysis_date=analysis_date,
                    total_conversations=total_chats,
                    conversations_with_repetitions=0,
                    repetition_percentage=0.0,
                    repetitions=[],
                    summary=summary
                )

            # Save results to file
            output_file = self.save_results(repetition_data, department, percentage, chats_with_reps, total_chats)

            logger.info(f"Repetitions results saved to {output_file}")

            # Upload to Google Sheets if requested
            if upload_to_sheets:
                try:
                    from .sheets_service import get_sheets_service
                    sheets_service = get_sheets_service()

                    spreadsheet_id = config.get('spreadsheet_id')
                    if spreadsheet_id:
                        sheet_name = f"Repetitions {analysis_date}"
                        success = sheets_service.upload_csv_to_sheet(
                            spreadsheet_id, output_file, sheet_name
                        )
                        if success:
                            logger.info(f"Successfully uploaded repetitions results for {department}")
                        else:
                            logger.warning(f"Failed to upload repetitions results for {department}")
                    else:
                        logger.warning(f"No spreadsheet ID configured for {department}")

                except Exception as e:
                    logger.error(f"Failed to upload repetitions data to Google Sheets: {e}")

            # Convert repetition_data to RepetitionRecord objects
            repetitions = []
            for record in repetition_data:
                repetitions.append(RepetitionRecord(
                    conversation_id=str(record.get('conversation_id', '')),
                    message_id=str(record.get('message_id', '')),
                    message=str(record.get('message', '')),
                    repetition_count=int(record.get('repetition_count', 0)),
                    skill=record.get('skill', None)
                ))

            # Create summary object
            summary = AnalysisSummary(
                message='TOTAL REPETITIONS' if repetitions else 'NO REPETITIONS FOUND',
                percentage_with_repetitions=f"{percentage:.2f}%",
                total_chats=total_chats,
                chats_with_repetitions=chats_with_reps
            )

            result = AnalysisResult(
                department=department,
                analysis_date=analysis_date,
                total_conversations=total_chats,
                conversations_with_repetitions=chats_with_reps,
                repetition_percentage=round(percentage, 2),
                repetitions=repetitions,
                summary=summary
            )

            logger.info(f"Repetitions analysis completed successfully for {department}")
            return result

        except Exception as e:
            logger.error(f"Repetitions analysis failed for {department}: {str(e)}")
            raise RuntimeError(f"Repetitions analysis failed for {department}: {str(e)}")
