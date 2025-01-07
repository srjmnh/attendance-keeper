from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.models.subject import Subject
import logging

subject = Blueprint('subject', __name__)
db = DatabaseService()
logger = logging.getLogger(__name__)

@subject.route('/')
@login_required
def list():
    """List all subjects"""
    try:
        if current_user.is_admin():
            subjects = db.get_all_subjects()
        elif current_user.is_teacher():
            subjects = db.get_teacher_subjects(current_user.id)
        else:  # student
            subjects = db.get_student_subjects(current_user.id)
        
        return render_template('subject/list.html', subjects=subjects)
    except Exception as e:
        logger.error(f"Error listing subjects: {str(e)}")
        flash('Error loading subjects', 'danger')
        return redirect(url_for('main.index'))

@subject.route('/view/<subject_id>')
@login_required
def view(subject_id):
    """View subject details"""
    try:
        subject = db.get_subject_by_id(subject_id)
        if not subject:
            flash('Subject not found', 'danger')
            return redirect(url_for('subject.list'))
        
        return render_template('subject/view.html', subject=subject)
    except Exception as e:
        logger.error(f"Error viewing subject: {str(e)}")
        flash('Error loading subject details', 'danger')
        return redirect(url_for('subject.list'))

@subject.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new subject"""
    if not current_user.is_teacher() and not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            subject_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'teacher_id': current_user.id if current_user.is_teacher() else request.form.get('teacher_id'),
                'class_name': request.form.get('class_name'),
                'division': request.form.get('division')
            }
            
            db.create_subject(subject_data)
            flash('Subject created successfully', 'success')
            return redirect(url_for('subject.list'))
            
        except Exception as e:
            logger.error(f"Error creating subject: {str(e)}")
            flash('Error creating subject', 'danger')
            return redirect(url_for('subject.create'))
    
    return render_template('subject/create.html') 