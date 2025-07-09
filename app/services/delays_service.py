"""
Delays analysis service for calculating response times
"""

import pandas as pd
import logging
import os
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.config import DEPARTMENT_CONFIG
from app.services.tableau_service import TableauService
from app.services.sheets_service import get_sheets_service

logger = logging.getLogger(__name__)

class DelaysAnalysisService:
    """Service for analyzing bot response times and delays."""

    def __init__(self):
        self.tableau_service = TableauService()

    def format_response_time_with_count(self, response_times_list):
        """
        Format response times as MM:SS with count of messages > 4 minutes.

        Args:
            response_times_list: List of response times in seconds

        Returns:
            String in format "MM:SS (X msg > 4 Min)" where MM:SS is average time
        """
        if not response_times_list:
            return "00:00 (0 msg > 4 Min)"

        # Calculate average response time
        avg_seconds = sum(response_times_list) / len(response_times_list)

        # Convert to minutes and seconds
        minutes = int(avg_seconds // 60)
        seconds = int(avg_seconds % 60)

        # Count messages over 4 minutes (240 seconds)
        over_4_min = sum(1 for time in response_times_list if time > 240)

        # Format as MM:SS
        time_formatted = f"{minutes:02d}:{seconds:02d}"

        return f"{time_formatted} ({over_4_min} msg > 4 Min)"

    def calculate_agent_intervention_percentage(self, department: str, df: pd.DataFrame) -> float:
        """
        Calculate the percentage of agent intervention.

        Args:
            department: Department name
            df: DataFrame with message data from Tableau

        Returns:
            Percentage of agent messages vs total (bot + agent) messages
        """
        try:
            logger.info(f"Calculating agent percentage for {department}")
            logger.info(f"Input DataFrame shape: {df.shape}")
            logger.info(f"DataFrame columns: {list(df.columns)}")

            # Check if required columns exist
            if "Message Type" not in df.columns:
                logger.error(f"Missing 'Message Type' column in DataFrame")
                return 0.0

            if "Sent By" not in df.columns:
                logger.error(f"Missing 'Sent By' column in DataFrame")
                return 0.0

            # Keep only rows with Message Type == "Normal Message"
            df_filtered = df[df["Message Type"].str.lower() == "normal message"].copy()
            logger.info(f"After filtering for 'normal message': {len(df_filtered)} rows")

            if len(df_filtered) == 0:
                logger.warning(f"No 'normal message' rows found for {department}")
                return 0.0

            # Count number of rows with Sent By == "Bot" and Sent By == "Agent"
            bot_count = (df_filtered["Sent By"].str.lower() == "bot").sum()
            agent_count = (df_filtered["Sent By"].str.lower() == "agent").sum()

            total = bot_count + agent_count
            percent = (agent_count / total * 100) if total > 0 else 0.0

            logger.info(f"Bot messages: {bot_count}")
            logger.info(f"Agent messages: {agent_count}")
            logger.info(f"Total bot+agent messages: {total}")
            logger.info(f"Agent intervention percentage: {percent:.2f}%")

            # Log unique values in Sent By column for debugging
            unique_senders = df_filtered["Sent By"].str.lower().unique()
            logger.info(f"Unique senders in filtered data: {list(unique_senders)}")

            return round(percent, 2)

        except Exception as e:
            logger.error(f"Error calculating agent percentage for {department}: {e}")
            logger.error(f"Exception details: {str(e)}")
            return 0.0

    def segment_conversation(self, conv_data, target_skills):
        """Segments a single conversation into parts based on agent or bot changes and marks messages with [IDENTIFIER] if conditions met."""
        segments = []
        current_segment = []
        current_agent = None
        first_agent_or_bot_encountered = False
        last_skill = None
        marking = False
        skill_name_length_limit = 23

        for index, row in conv_data.iterrows():
            sender = str(row["Sent By"]).strip().lower()
            message = row["TEXT"]
            skill = row["Skill"]

            # Check marking condition using flexible case-insensitive contains matching
            skill_lower = str(skill).lower()
            target_skills_lower = [str(ts).lower() for ts in target_skills]

            if last_skill is None:
                # Check if any target skill is contained in current skill (case-insensitive)
                for target_skill_lower in target_skills_lower:
                    if target_skill_lower in skill_lower or skill_lower in target_skill_lower:
                        marking = True
                        break
            elif marking and (len(skill) > skill_name_length_limit):
                marking = False

            # Identify if it's from agent or bot
            if sender in ["agent", "bot"]:
                if not first_agent_or_bot_encountered:
                    current_agent = row["Agent Name "] if sender == "agent" else "BOT"
                    first_agent_or_bot_encountered = True
                else:
                    next_agent = row["Agent Name "] if sender == "agent" else "BOT"
                    if next_agent != current_agent:
                        if current_segment:
                            segments.append((current_agent, last_skill, current_segment))
                            current_segment = []
                        current_agent = next_agent

                last_skill = skill  # Always update skill on agent/bot message

            # Add [IDENTIFIER] if marking is True and sender is agent or bot
            if marking and sender in ["agent", "bot"]:
                current_segment.append(f"[IDENTIFIER] {sender.capitalize()}: {message}")
            else:
                current_segment.append(f"{sender.capitalize()}: {message}")

        # Add final segment
        if current_segment:
            segments.append((current_agent, last_skill, current_segment))

        return segments

    def process_conversations(self, df, target_skills):
        """Process conversations and segment them, aggregating by Conversation ID."""


        # Track conversations that contain target skills
        target_skill_conversations = set()

        # Debug: Log unique skills in the data
        unique_skills = df["Skill"].unique()
        logger.info(f"Unique skills in data: {list(unique_skills)[:10]}...")  # Show first 10
        logger.info(f"Total unique skills: {len(unique_skills)}")

        # Use flexible case-insensitive contains matching
        target_skills_lower = [str(skill).lower() for skill in target_skills]
        logger.info(f"Target skills (lowercase): {target_skills_lower}")

        for conv_id, conv_data in df.groupby("Conversation ID"):
            conv_skills = [str(skill).lower() for skill in conv_data["Skill"].values]

            # Check if any target skill is contained in any conversation skill (case-insensitive)
            for target_skill_lower in target_skills_lower:
                for conv_skill_lower in conv_skills:
                    if target_skill_lower in conv_skill_lower or conv_skill_lower in target_skill_lower:
                        target_skill_conversations.add(conv_id)
                        logger.debug(f"Match found: '{target_skill_lower}' matches '{conv_skill_lower}' in conversation {conv_id}")
                        break
                if conv_id in target_skill_conversations:
                    break

        logger.info(f"Found {len(target_skill_conversations)} conversations with target skills using flexible matching")

        all_segments = []
        customer_name_map = df.groupby("Conversation ID")["Customer Name"].first().to_dict()

        for conv_id, conv_data in df.groupby("Conversation ID"):
            if conv_id not in target_skill_conversations:
                continue
            conv_data = conv_data[conv_data["Message Type"] == "Normal Message"]
            segments = self.segment_conversation(conv_data, target_skills)
            customer_name = customer_name_map.get(conv_id, "")
            for agent, last_skill, segment_messages in segments:
                all_segments.append([
                    conv_id,
                    customer_name,
                    last_skill,
                    agent,
                    "\n".join(segment_messages)
                ])

        segmented_df = pd.DataFrame(
            all_segments,
            columns=["Conversation ID", "Customer Name", "Last Skill", "Agent Name", "Messages"]
        )

        # Filter: keep only segments that include consumer messages
        segmented_df = segmented_df[segmented_df["Messages"].str.contains("Consumer:", na=False)]

        # Keep only conversations that used target skills
        segmented_df = segmented_df[segmented_df["Conversation ID"].isin(target_skill_conversations)]

        # Aggregate by Conversation ID (not Customer Name)
        agg_functions = {
            'Customer Name': 'first',
            'Last Skill': 'first',
            'Agent Name': lambda x: ', '.join(x.astype(str).unique()),
            'Messages': lambda x: '\n\n--- CONVERSATION SEPARATOR ---\n\n'.join(x.astype(str))
        }

        merged_df = segmented_df.groupby('Conversation ID').agg(agg_functions).reset_index()
        merged_df['Conversation ID'] = merged_df['Conversation ID'].astype(str)

        return merged_df

    def calculate_handling_percentage(self, department: str, df: pd.DataFrame) -> float:
        """
        Calculate the percentage of handling (bot-only conversations vs all conversations).
        Uses the same logic as get_bot_handle_metrics function.

        Args:
            department: Department name
            df: DataFrame with message data from Tableau

        Returns:
            Percentage of conversations handled by bot only
        """
        try:
            logger.info(f"Calculating handling percentage for {department}")

            # Get target skills for the department
            from app.config import DEPARTMENT_CONFIG
            config = DEPARTMENT_CONFIG.get(department, {})
            target_skills = config.get('skill_filter', [])

            if isinstance(target_skills, str):
                target_skills = [target_skills]

            logger.info(f"Target skills for {department}: {target_skills}")

            # Find skill columns (case-insensitive)
            skill_columns = [col for col in df.columns if 'skill' in col.lower()]

            if not skill_columns:
                logger.warning("No skill columns found in the dataset")
                return 0.0

            logger.info(f"Found skill columns: {skill_columns}")

            # Group by conversation ID
            conversation_groups = df.groupby('Conversation ID')

            fully_bot_conversations = []
            total_chats_with_skill = 0

            for conversation_id, group in conversation_groups:
                # Check if the conversation has any of the specified skills (flexible matching)
                has_skill = False
                for col in skill_columns:
                    col_values = group[col].astype(str).str.lower()
                    for target_skill in target_skills:
                        target_skill_lower = str(target_skill).lower()
                        # Use flexible contains matching
                        if col_values.str.contains(target_skill_lower, na=False).any():
                            has_skill = True
                            break
                    if has_skill:
                        break

                if not has_skill:
                    continue  # Skip conversations without the specified skill

                total_chats_with_skill += 1

                # Check if there are any Agent interactions based on "Agent Name " column
                has_agent_interaction = group['Agent Name '].notna().any()

                if has_agent_interaction:
                    continue  # Skip conversations with Agent interaction

                # Check if all messages are bot messages
                # Bot messages are identified by having no Agent Name (isna)
                all_bot_messages = group['Agent Name '].isna().all()

                if not all_bot_messages:
                    continue  # Skip if not all messages are bot messages

                # If we reach here, it's a fully bot-handled conversation
                fully_bot_conversations.append(conversation_id)

            # Calculate bot handle ratio
            total_chats = total_chats_with_skill  # Use skill-filtered total
            bot_handle_ratio = (len(fully_bot_conversations) / total_chats) * 100 if total_chats > 0 else 0

            logger.info(f"Total chats with target skills: {total_chats_with_skill}")
            logger.info(f"Conversations handled fully by bot: {len(fully_bot_conversations)}")
            logger.info(f"Bot Handle Ratio: {bot_handle_ratio:.2f}%")

            return round(bot_handle_ratio, 2)

        except Exception as e:
            logger.error(f"Error calculating handling percentage for {department}: {e}")
            logger.error(f"Exception details: {str(e)}")
            return 0.0
    
    def calculate_first_response_times(self, df: pd.DataFrame, keywords: list = None) -> pd.DataFrame:
        """Calculate first response times for bot messages."""
        logger.info(f"Starting first response calculation with skill filters: {keywords}")

        df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'])
        response_times = []

        for conv_id, group in df.groupby("Conversation ID"):
            group = group[
                (group['Message Type'].str.lower().isin(['normal message', 'transfer'])) |
                ((group['Message Type'].str.lower() == 'private message') & (group['Sent By'].str.lower() == 'system'))
            ].copy()
            first_consumer_message_time = None
            first_response_recorded = False
            for i in range(len(group)):
                current_row = group.iloc[i]
                sender = str(current_row["Sent By"]).strip().lower()
                message_type = str(current_row["Message Type"]).strip().lower()
                skill = str(current_row["Skill"]).strip().lower()

                if sender == "consumer" and first_consumer_message_time is None:
                    first_consumer_message_time = current_row["Message Sent Time"]

                elif message_type == "transfer" and first_consumer_message_time is not None:
                    first_consumer_message_time = current_row["Message Sent Time"]

                elif sender == "system" and message_type == 'private message' and first_consumer_message_time is not None:
                    first_consumer_message_time = current_row['Message Sent Time']

                elif sender in ["bot", "agent", "system"] and first_consumer_message_time is not None and not first_response_recorded:
                    time_diff = (current_row["Message Sent Time"] - first_consumer_message_time).total_seconds()
                    time_diff = round(time_diff, 2)

                    if time_diff < 0:
                        logger.warning(f"Negative first response time {time_diff} for conversation {conv_id}, message {current_row.get('MESSAGE_ID', 'N/A')} - skipping")
                    if time_diff < 0:
                                #logging negative response times
                                logging.info(f"Negative response time detected for conversation {conv_id} by {sender_name}: {time_diff} seconds")
                                logging.info(f"First consumer message time is {first_consumer_message_time} seconds")
                                logging.info(f"Message ID is {current_row.get('MESSAGE_ID', '')}")    

                    if sender == "bot":
                        sender_name = "BOT" + "_" + skill
                    elif sender == "agent":
                        sender_name = current_row.get("Agent Name ", current_row.get("Agent Name", "Unknown_Agent"))
                    else:
                        sender_name = "System"

                    if str(sender_name).lower().find("bot") != -1:
                        response_times.append({
                            "Conversation Id": conv_id,
                            "Sender": sender_name,
                            "Response Time (secs)": time_diff,
                            "Message Id": current_row.get("MESSAGE_ID", ""),
                            "Skill": skill,
                            "Message Sent Time": current_row["Message Sent Time"]
                        })
                        first_response_recorded = True
                        break

        result_df = pd.DataFrame(response_times)
        if keywords:
            result_df['Sender'] = result_df['Sender'].astype(str)
            mask = result_df['Sender'].str.contains('|'.join(keywords), case=False, na=False)
            result_df = result_df[mask]
        if not result_df.empty:
            result_df = result_df.sort_values(by='Response Time (secs)', ascending=False)
        logger.info(f"Final result DataFrame shape: {result_df.shape}")
        return result_df

    def calculate_subsequent_response_times(self, df: pd.DataFrame, keywords: list = None) -> pd.DataFrame:
        """Calculate Non initial Response times (excluding first response)."""
        logger.info(f"Starting subsequent response calculation with skill filters: {keywords}")

        df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'], infer_datetime_format=True)
        response_times = []

        for conv_id, group in df.groupby("Conversation ID"):
            group = group[
                (group['Message Type'].str.lower().isin(['normal message', 'transfer'])) |
                ((group['Message Type'].str.lower() == 'private message') & (group['Sent By'].str.lower() == 'system'))
            ].copy()
            first_consumer_message_time = None
            first_response_recorded = False

            for i in range(len(group)):
                current_row = group.iloc[i]
                sender = str(current_row["Sent By"]).strip().lower()
                message_type = str(current_row["Message Type"]).strip().lower()
                skill = str(current_row["Skill"]).strip().lower()

                if sender == "consumer" and first_consumer_message_time is None:
                    first_consumer_message_time = current_row["Message Sent Time"]

                elif message_type == "transfer" and first_consumer_message_time is not None:
                    first_consumer_message_time = current_row["Message Sent Time"]

                elif sender == "system" and message_type == 'private message' and first_consumer_message_time is not None:
                    first_consumer_message_time = current_row['Message Sent Time']

                elif sender in ["bot", "agent", "system"] and first_consumer_message_time is not None:
                    # Skip the first response (we only want subsequent responses)
                    if not first_response_recorded:
                        first_response_recorded = True
                        first_consumer_message_time = None
                        # Don't reset first_consumer_message_time here - keep it for subsequent responses
                        continue

                    # Calculate response time for subsequent responses
                    time_diff = (current_row["Message Sent Time"] - first_consumer_message_time).total_seconds()
                    time_diff = round(time_diff, 2)
                    if time_diff < 0:
                                #logging negative response times
                                logging.info(f"Negative response time detected for conversation {conv_id} by {sender_name}: {time_diff} seconds")
                                logging.info(f"First consumer message time is {first_consumer_message_time} seconds")
                                logging.info(f"Message ID is {current_row.get('MESSAGE_ID', '')}")
                    # Determine sender name
                    if sender == "bot":
                        sender_name = "BOT" + "_" + skill
                    elif sender == "agent":
                        sender_name = current_row.get("Agent Name ", current_row.get("Agent Name", "Unknown_Agent"))
                    else:
                        sender_name = "System"

                    # Only record bot responses (filter out agent/system responses)
                    if str(sender_name).lower().find("bot") != -1:
                        response_times.append({
                            "Conversation Id": conv_id,
                            "Sender": sender_name,
                            "Response Time (secs)": time_diff,
                            "Message Id": current_row.get("MESSAGE_ID", ""),
                            "Skill": skill,
                            "Message Sent Time": current_row["Message Sent Time"]
                        })
                        # Reset for next consumer message
                        first_consumer_message_time = None

        result_df = pd.DataFrame(response_times)

        # Apply skill filter if provided (using keywords logic from your working code)
        if keywords:
            result_df['Sender'] = result_df['Sender'].astype(str)  # Ensure all values are strings
            mask = result_df['Sender'].str.contains('|'.join(keywords), case=False, na=False)
            result_df = result_df[mask]

        if not result_df.empty:
            result_df = result_df.sort_values(by='Response Time (secs)', ascending=False)

        logger.info(f"Final subsequent response DataFrame shape: {result_df.shape}")
        return result_df

    def preprocess_data(self, df: pd.DataFrame, department: str = None) -> pd.DataFrame:
        """Preprocess data for delays analysis."""
        # Sort by conversation ID and message sent time
        df["Message Sent Time"] = pd.to_datetime(df["Message Sent Time"])
        df = df.sort_values(by=['Conversation ID', 'Message Sent Time'])

        # Count before dropping duplicates
        original_count = len(df)

        # Drop duplicates
        df = df.drop_duplicates(subset=['Conversation ID', 'Message Sent Time'], keep='first')

        # Count after dropping duplicates
        duplicates_removed = original_count - len(df)
        logger.info(f"Removed {duplicates_removed} duplicate records from {original_count} total records")

        # Save cleaned data to CSV if department is provided
        if department:
            try:
                from app.config import DEPARTMENT_CONFIG
                config = DEPARTMENT_CONFIG.get(department, {})
                cleaned_file = config.get('cleaned_file')

                if cleaned_file:
                    # Modify the filename for delays analysis
                    delays_cleaned_file = cleaned_file.replace('_cleaned_repetitions.csv', '_delays_cleaned.csv')
                    df.to_csv(delays_cleaned_file, index=False)
                    logger.info(f"Saved cleaned delays data to {delays_cleaned_file}")
                else:
                    # Fallback filename
                    delays_cleaned_file = f"data/temp/{department}_delays_cleaned.csv"
                    df.to_csv(delays_cleaned_file, index=False)
                    logger.info(f"Saved cleaned delays data to {delays_cleaned_file}")
            except Exception as e:
                logger.warning(f"Failed to save cleaned delays data: {e}")

        # Ensure required columns exist
        required_columns = ['Conversation ID', 'Message Sent Time', 'Sent By', 'Message Type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        return df

    def save_delays_results(self, first_response_df: pd.DataFrame, subsequent_response_df: pd.DataFrame,
                           department: str, analysis_date: str) -> Tuple[str, str]:
        """Save delays analysis results to CSV files with average row."""
        # Create output file paths
        first_response_file = f"data/output/delays_first_response_{department}_{analysis_date}.csv"
        subsequent_response_file = f"data/output/delays_subsequent_response_{department}_{analysis_date}.csv"

        # Add average row to first response data
        if not first_response_df.empty:
            first_response_with_avg = self._add_average_row(first_response_df, "First Response")
            first_response_with_avg.to_csv(first_response_file, index=False)
        else:
            first_response_df.to_csv(first_response_file, index=False)

        # Add average row to Non initial Response data
        if not subsequent_response_df.empty:
            subsequent_response_with_avg = self._add_average_row(subsequent_response_df, "Non initial Response")
            subsequent_response_with_avg.to_csv(subsequent_response_file, index=False)
        else:
            subsequent_response_df.to_csv(subsequent_response_file, index=False)

        logger.info(f"Delays results saved to {first_response_file} and {subsequent_response_file}")

        return first_response_file, subsequent_response_file

    def _add_average_row(self, df: pd.DataFrame, response_type: str) -> pd.DataFrame:
        """Add an average row to the bottom of the DataFrame."""
        if df.empty or 'Response Time (secs)' not in df.columns:
            return df

        # Create a copy to avoid modifying the original
        df_with_avg = df.copy()

        # drop all row with Response Time (secs) more than four minutes
        df_with_avg = df_with_avg[df_with_avg['Response Time (secs)'] <= 240]
        # Calculate averages
        avg_response_time = df['Response Time (secs)'].mean()

        # Create average row
        avg_row = {}
        for col in df.columns:
            if col == 'Conversation Id':
                avg_row[col] = f"AVERAGE ({response_type})"
            elif col == 'Sender':
                avg_row[col] = "AVERAGE"
            elif col == 'Response Time (secs)':
                avg_row[col] = round(avg_response_time, 2)
            elif col == 'Message Id':
                avg_row[col] = f"Count: {len(df)}"
            elif col == 'Skill':
                # Show the most common skill
                if not df[col].empty:
                    most_common_skill = df[col].mode()
                    avg_row[col] = most_common_skill.iloc[0] if len(most_common_skill) > 0 else "AVERAGE"
                else:
                    avg_row[col] = "AVERAGE"
            elif col == 'Message Sent Time':
                avg_row[col] = f"Avg: {avg_response_time/60:.1f} min"
            else:
                avg_row[col] = ""

        # Add the average row
        avg_df = pd.DataFrame([avg_row])
        result_df = pd.concat([df_with_avg, avg_df], ignore_index=True)

        return result_df
    async def analyze_department_delays(self, department: str,df: pd.DataFrame, upload_to_sheets: bool = True, 
                                      date_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze response time delays for a specific department.
        
        Args:
            department: Department name
            upload_to_sheets: Whether to upload results to Google Sheets
            date_override: Override analysis date (YYYY-MM-DD)
        
        Returns:
            Dictionary with analysis results
        """
        if department not in DEPARTMENT_CONFIG:
            raise ValueError(f"Unknown department: {department}")
        
        config = DEPARTMENT_CONFIG[department]
        
        try:
            # Fetch data from Tableau
            logger.info(f"Fetching data for {department} delays analysis from Tableau")
            
            # Determine date range
            if date_override:
                start_date = end_date = date_override
                analysis_date = date_override
            else:
                yesterday = datetime.now() - timedelta(days=1)
                start_date = end_date = yesterday.strftime("%Y-%m-%d")
                analysis_date = start_date
            
  

            if df.empty:
                logger.warning(f"No data rows found for {department} on {analysis_date}")
                return {
                    "department": department,
                    "analysis_date": analysis_date,
                    "status": "NO_DATA",
                    "message": "No data rows found for the specified date"
                }
            
            df = self.preprocess_data(df, department)
            
            # Calculate response times
            skill_filter = config.get('skill_filter')
            logger.info(f"Calculating response times with skill filters: {skill_filter}")
            
            first_response_df = self.calculate_first_response_times(df, skill_filter)
            subsequent_response_df = self.calculate_subsequent_response_times(df, skill_filter)

            logger.info(f"First response calculations: {len(first_response_df)} rows")
            logger.info(f"Non initial Response calculations: {len(subsequent_response_df)} rows")
            
            try:
                agent_percentage = self.calculate_agent_intervention_percentage(department, df.copy())
                logger.info(f"Agent percentage calculated successfully: {agent_percentage}%")
            except Exception as e:
                logger.error(f"Failed to calculate agent percentage: {e}")
                agent_percentage = 0.0

            # Calculate handling percentage
            try:
                handling_percentage = self.calculate_handling_percentage(department, df.copy())
                logger.info(f"Handling percentage calculated successfully: {handling_percentage}%")
            except Exception as e:
                logger.error(f"Failed to calculate handling percentage: {e}")
                handling_percentage = 0.0
            # Save results
            first_file, subsequent_file = self.save_delays_results(
                first_response_df, subsequent_response_df, department, analysis_date
            )
            
            # Calculate summary statistics
            summary = self.calculate_summary_stats(first_response_df, subsequent_response_df)
            summary["agent_intervention"] = {
                "percentage": agent_percentage,
                "formatted": f"{agent_percentage:.2f}%"
            }
            summary["handling"] = {
                "percentage": handling_percentage,
                "formatted": f"{handling_percentage:.2f}%"
            }
            # Upload to Google Sheets if requested
            if upload_to_sheets:
                await self.upload_to_delays_sheets(
                    department, first_response_df, subsequent_response_df, analysis_date
                )
            
            result = {
                "department": department,
                "analysis_date": analysis_date,
                "status": "SUCCESS",
                "summary": summary,
                "files": {
                    "first_response": first_file,
                    "subsequent_response": subsequent_file
                },
                "data_counts": {
                    "total_conversations": df['Conversation ID'].nunique(),
                    "first_responses": len(first_response_df),
                    "subsequent_responses": len(subsequent_response_df)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing delays for {department}: {e}")
            raise RuntimeError(f"Delays analysis failed for {department}: {str(e)}")

    async def analyze_department_delays_with_data(self, department: str, df: pd.DataFrame,
                                                analysis_date: str, upload_to_sheets: bool = True) -> Dict[str, Any]:
        """
        Analyze response time delays for a department using pre-loaded data.

        This method is optimized for combined analysis where data is already fetched.

        Args:
            department: Department name
            df: Pre-loaded DataFrame with conversation data
            analysis_date: Date of analysis (YYYY-MM-DD format)
            upload_to_sheets: Whether to upload results to Google Sheets

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting delays analysis for {department} with pre-loaded data")

        try:
            # Get department configuration
            config = DEPARTMENT_CONFIG[department]
            skill_filter = config['skill_filter']

            logger.info(f"Processing {len(df)} rows for {department} delays with skill filters: {skill_filter}")

            # Preprocess the data (drop duplicates and save cleaned data)
            df = self.preprocess_data(df, department)

            # Calculate response times
            first_response_df = self.calculate_first_response_times(df, skill_filter)
            subsequent_response_df = self.calculate_subsequent_response_times(df, skill_filter)

            logger.info(f"First response calculations: {len(first_response_df)} rows")
            logger.info(f"Non initial Response calculations: {len(subsequent_response_df)} rows")

            # Save results to files (same order as individual method)
            first_response_file, subsequent_response_file = self.save_delays_results(
                first_response_df, subsequent_response_df, department, analysis_date
            )

            # Calculate agent intervention percentage
            try:
                agent_percentage = self.calculate_agent_intervention_percentage(department, df)
                logger.info(f"Agent percentage calculated successfully: {agent_percentage}%")
            except Exception as e:
                logger.error(f"Failed to calculate agent percentage: {e}")
                agent_percentage = 0.0

            # Calculate handling percentage
            try:
                handling_percentage = self.calculate_handling_percentage(department, df)
                logger.info(f"Handling percentage calculated successfully: {handling_percentage}%")
            except Exception as e:
                logger.error(f"Failed to calculate handling percentage: {e}")
                handling_percentage = 0.0

            # Generate summary statistics (same as working individual delays method)
            summary = self.calculate_summary_stats(first_response_df, subsequent_response_df)

            # Add agent percentage and handling percentage to summary
            summary["agent_intervention"] = {
                "percentage": agent_percentage,
                "formatted": f"{agent_percentage:.2f}%"
            }

            summary["handling"] = {
                "percentage": handling_percentage,
                "formatted": f"{handling_percentage:.2f}%"
            }

            # Upload to Google Sheets if requested
            if upload_to_sheets:
                logger.info(f"Starting Google Sheets upload for {department} delays")
                try:
                    await self.upload_to_delays_sheets(
                        department, first_response_df, subsequent_response_df, analysis_date
                    )
                    logger.info(f"Completed Google Sheets upload for {department} delays")
                except Exception as e:
                    logger.error(f"Failed to upload delays data to Google Sheets: {e}")
                    import traceback
                    logger.error(f"Upload error traceback: {traceback.format_exc()}")
            else:
                logger.info(f"Skipping Google Sheets upload for {department} delays (upload_to_sheets=False)")

            # Count conversations for summary
            total_conversations = df['Conversation ID'].nunique() if 'Conversation ID' in df.columns else len(df)

            result = {
                "department": department,
                "analysis_date": analysis_date,
                "status": "SUCCESS",
                "summary": summary,
                "files": {
                    "first_response": first_response_file,
                    "subsequent_response": subsequent_response_file
                },
                "data_counts": {
                    "total_conversations": total_conversations,
                    "first_responses": len(first_response_df),
                    "subsequent_responses": len(subsequent_response_df)
                }
            }

            logger.info(f"Delays analysis completed successfully for {department}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing delays for {department}: {e}")
            raise RuntimeError(f"Delays analysis failed for {department}: {str(e)}")

    def calculate_summary_stats(self, first_response_df: pd.DataFrame, 
                               subsequent_response_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for response times."""
        summary = {}
        
        if not first_response_df.empty:
            response_times = first_response_df['Response Time (secs)']

            # Filter for responses < 4 minutes (240 seconds) for average calculation
            response_times_under_4min = response_times[response_times < 240]

            # Calculate stats using filtered data (< 4 minutes only)
            if not response_times_under_4min.empty:
                avg_time = response_times_under_4min.mean()
                median_time = response_times_under_4min.median()
                min_time = response_times_under_4min.min()
            else:
                avg_time = median_time = min_time = 0.0

            # Max time uses all data (for reference)
            max_time = response_times.max()

            # Count responses >= 4 minutes
            count_4plus = len(response_times[response_times >= 240])

            # Format response time as MM:SS with count over 4 minutes (uses all data)
            formatted_time = self.format_response_time_with_count(response_times.tolist())

            summary["first_response"] = {
                "count": len(first_response_df),
                "count_under_4min": len(response_times_under_4min),
                "count_4plus": count_4plus,
                "avg_response_time": round(float(avg_time), 2) if not pd.isna(avg_time) else 0.0,
                "avg_response_time_formatted": formatted_time,
                "median_response_time": round(float(median_time), 2) if not pd.isna(median_time) else 0.0,
                "max_response_time": round(float(max_time), 2) if not pd.isna(max_time) else 0.0,
                "min_response_time": round(float(min_time), 2) if not pd.isna(min_time) else 0.0
            }
        else:
            summary["first_response"] = {
                "count": 0,
                "count_under_4min": 0,
                "count_4plus": 0,
                "message": "No first responses found",
                "avg_response_time_formatted": "00:00 (0 msg > 4 Min)"
            }

        if not subsequent_response_df.empty:
            response_times = subsequent_response_df['Response Time (secs)']

            # Filter for responses < 4 minutes (240 seconds) for average calculation
            response_times_under_4min = response_times[response_times < 240]

            # Calculate stats using filtered data (< 4 minutes only)
            if not response_times_under_4min.empty:
                avg_time = response_times_under_4min.mean()
                median_time = response_times_under_4min.median()
                min_time = response_times_under_4min.min()
            else:
                avg_time = median_time = min_time = 0.0

            # Max time uses all data (for reference)
            max_time = response_times.max()

            # Count responses >= 4 minutes
            count_4plus = len(response_times[response_times >= 240])

            # Format response time as MM:SS with count over 4 minutes (uses all data)
            formatted_time = self.format_response_time_with_count(response_times.tolist())

            summary["subsequent_response"] = {
                "count": len(subsequent_response_df),
                "count_under_4min": len(response_times_under_4min),
                "count_4plus": count_4plus,
                "avg_response_time": round(float(avg_time), 2) if not pd.isna(avg_time) else 0.0,
                "avg_response_time_formatted": formatted_time,
                "median_response_time": round(float(median_time), 2) if not pd.isna(median_time) else 0.0,
                "max_response_time": round(float(max_time), 2) if not pd.isna(max_time) else 0.0,
                "min_response_time": round(float(min_time), 2) if not pd.isna(min_time) else 0.0
            }
        else:
            summary["subsequent_response"] = {
                "count": 0,
                "count_under_4min": 0,
                "count_4plus": 0,
                "message": "No Non initial Responses found",
                "avg_response_time_formatted": "00:00 (0 msg > 4 Min)"
            }
        
        return summary

    async def upload_to_delays_sheets(self, department: str, first_response_df: pd.DataFrame,
                                    subsequent_response_df: pd.DataFrame, analysis_date: str):
        """Upload delays analysis results to Google Sheets."""
        try:
            # Check for delays-specific spreadsheet ID first
            delays_spreadsheet_id = os.getenv(f"{department.upper()}_DELAYS_SPREADSHEET_ID")
            logger.info(f"Checking delays spreadsheet ID for {department}: {delays_spreadsheet_id}")

            if not delays_spreadsheet_id:
                # Fallback to main spreadsheet ID if delays-specific one not configured
                delays_spreadsheet_id = os.getenv(f"{department.upper()}_SPREADSHEET_ID")
                if delays_spreadsheet_id:
                    logger.info(f"Using main spreadsheet for {department} delays (no delays-specific sheet configured)")
                    logger.info(f"Main spreadsheet ID: {delays_spreadsheet_id}")
                else:
                    logger.warning(f"No spreadsheet ID configured for {department} delays analysis")
                    return
            else:
                logger.info(f"Using delays-specific spreadsheet for {department}: {delays_spreadsheet_id}")
            
            sheets_service = get_sheets_service()

            logger.info(f"Preparing to upload delays data for {department}")
            logger.info(f"First response DataFrame: {len(first_response_df)} rows")
            logger.info(f"Non initial Response DataFrame: {len(subsequent_response_df)} rows")

            # Upload first response times with average row
            first_response_sheet_name = f"First Response {analysis_date}"
            if not first_response_df.empty:
                # Add average row and save to temporary CSV for upload
                first_response_with_avg = self._add_average_row(first_response_df, "First Response")
                temp_first_file = f"data/temp/delays_first_response_{department}_temp.csv"
                first_response_with_avg.to_csv(temp_first_file, index=False)

                success = sheets_service.upload_csv_to_sheet(
                    delays_spreadsheet_id, temp_first_file, first_response_sheet_name
                )
                if success:
                    logger.info(f"Successfully uploaded first response times with average for {department}")
                else:
                    logger.warning(f"Failed to upload first response times for {department}")
            else:
                logger.info(f"Skipping first response upload - DataFrame is empty for {department}")

            # Upload Non initial Response times with average row
            subsequent_response_sheet_name = f"Non initial Response {analysis_date}"
            if not subsequent_response_df.empty:
                # Add average row and save to temporary CSV for upload
                subsequent_response_with_avg = self._add_average_row(subsequent_response_df, "Non initial Response")
                temp_subsequent_file = f"data/temp/delays_subsequent_response_{department}_temp.csv"
                subsequent_response_with_avg.to_csv(temp_subsequent_file, index=False)

                success = sheets_service.upload_csv_to_sheet(
                    delays_spreadsheet_id, temp_subsequent_file, subsequent_response_sheet_name
                )
                if success:
                    logger.info(f"Successfully uploaded Non initial Response times with average for {department}")
                else:
                    logger.warning(f"Failed to upload Non initial Response times for {department}")
            else:
                logger.info(f"Skipping Non initial Response upload - DataFrame is empty for {department}")

        except Exception as e:
            logger.warning(f"Failed to upload delays data to Google Sheets for {department}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
