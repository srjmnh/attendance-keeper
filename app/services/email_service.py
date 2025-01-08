from flask import current_app, render_template
from flask_mail import Mail, Message
from threading import Thread
from datetime import datetime

mail = Mail()

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")

def send_email(subject, recipients, template, **kwargs):
    """Send an email using a template
    
    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        template: Name of the HTML template to use
        **kwargs: Variables to pass to the template
    """
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Render templates
        msg.html = render_template(f'email/{template}.html', **kwargs)
        msg.body = render_template(f'email/{template}.txt', **kwargs)
        
        # Send asynchronously
        Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        ).start()
        
    except Exception as e:
        current_app.logger.error(f"Error preparing email: {str(e)}")
        raise

def send_attendance_notification(user_email, student_name, subject_name, status, timestamp):
    """Send attendance notification email
    
    Args:
        user_email: Recipient's email address
        student_name: Name of the student
        subject_name: Name of the subject
        status: Attendance status (present/absent)
        timestamp: When the attendance was recorded
    """
    try:
        send_email(
            subject='Attendance Update',
            recipients=[user_email],
            template='attendance_notification',
            student_name=student_name,
            subject_name=subject_name,
            status=status,
            timestamp=timestamp,
            date=datetime.fromisoformat(timestamp).strftime('%B %d, %Y'),
            time=datetime.fromisoformat(timestamp).strftime('%I:%M %p')
        )
    except Exception as e:
        current_app.logger.error(f"Error sending attendance notification: {str(e)}")

def send_password_reset(user_email, reset_token):
    """Send password reset email
    
    Args:
        user_email: User's email address
        reset_token: Password reset token
    """
    try:
        send_email(
            subject='Reset Your Password',
            recipients=[user_email],
            template='password_reset',
            reset_token=reset_token,
            expiry_time='1 hour'  # Token expiry time
        )
    except Exception as e:
        current_app.logger.error(f"Error sending password reset email: {str(e)}")

def send_welcome_email(user_email, user_name):
    """Send welcome email to new users
    
    Args:
        user_email: User's email address
        user_name: User's name
    """
    try:
        send_email(
            subject='Welcome to AttendanceAI',
            recipients=[user_email],
            template='welcome',
            user_name=user_name
        )
    except Exception as e:
        current_app.logger.error(f"Error sending welcome email: {str(e)}")

def send_attendance_report(user_email, student_name, report_data):
    """Send attendance report email
    
    Args:
        user_email: Recipient's email address
        student_name: Name of the student
        report_data: Dictionary containing attendance statistics
    """
    try:
        send_email(
            subject='Attendance Report',
            recipients=[user_email],
            template='attendance_report',
            student_name=student_name,
            report_data=report_data,
            generated_date=datetime.utcnow().strftime('%B %d, %Y')
        )
    except Exception as e:
        current_app.logger.error(f"Error sending attendance report: {str(e)}")

def send_low_attendance_alert(user_email, student_name, subject_name, attendance_percentage):
    """Send low attendance alert email
    
    Args:
        user_email: Recipient's email address
        student_name: Name of the student
        subject_name: Name of the subject
        attendance_percentage: Current attendance percentage
    """
    try:
        send_email(
            subject='Low Attendance Alert',
            recipients=[user_email],
            template='low_attendance_alert',
            student_name=student_name,
            subject_name=subject_name,
            attendance_percentage=attendance_percentage,
            minimum_required=75  # Minimum required attendance percentage
        )
    except Exception as e:
        current_app.logger.error(f"Error sending low attendance alert: {str(e)}") 