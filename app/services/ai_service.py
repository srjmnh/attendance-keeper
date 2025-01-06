import google.generativeai as genai
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key):
        """Initialize the AI service with Gemini API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_attendance_insights(self, attendance_records):
        """Generate insights from attendance records using Gemini AI."""
        try:
            if not attendance_records:
                return {'insights': ['No attendance records available for analysis.']}

            # Prepare data for analysis
            total_records = len(attendance_records)
            present_count = len([r for r in attendance_records if r['status'].upper() == 'PRESENT'])
            absent_count = total_records - present_count
            attendance_rate = (present_count / total_records * 100) if total_records > 0 else 0

            # Group records by subject
            subject_stats = {}
            for record in attendance_records:
                subject = record['subject_name']
                if subject not in subject_stats:
                    subject_stats[subject] = {'present': 0, 'total': 0}
                subject_stats[subject]['total'] += 1
                if record['status'].upper() == 'PRESENT':
                    subject_stats[subject]['present'] += 1

            # Prepare prompt for Gemini
            prompt = f"""
            Analyze the following attendance data and provide 3-4 concise, actionable insights:

            Overall Statistics:
            - Total Records: {total_records}
            - Present: {present_count}
            - Absent: {absent_count}
            - Attendance Rate: {attendance_rate:.1f}%

            Subject-wise Statistics:
            {self._format_subject_stats(subject_stats)}

            Please focus on:
            1. Attendance patterns and trends
            2. Subjects with notably high or low attendance
            3. Actionable recommendations for improvement
            4. Any concerning patterns that need attention

            Format each insight as a clear, concise bullet point.
            """

            # Generate insights using Gemini
            response = self.model.generate_content(prompt)
            insights = self._parse_insights(response.text)

            return {'insights': insights}

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return {
                'insights': [
                    'Unable to generate insights at this time.',
                    'Please try again later or contact support if the issue persists.'
                ]
            }

    def _format_subject_stats(self, subject_stats):
        """Format subject statistics for the prompt."""
        formatted_stats = []
        for subject, stats in subject_stats.items():
            rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
            formatted_stats.append(
                f"- {subject}: {stats['present']}/{stats['total']} classes "
                f"({rate:.1f}% attendance)"
            )
        return '\n'.join(formatted_stats)

    def _parse_insights(self, response_text):
        """Parse and format insights from Gemini's response."""
        # Split response into lines and clean up
        lines = response_text.strip().split('\n')
        insights = []
        
        for line in lines:
            # Clean up the line
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Remove bullet points and other markers
            line = line.lstrip('•-*').strip()
            # Add to insights if not empty
            if line:
                insights.append(line)

        # Limit to 4 insights
        return insights[:4] 