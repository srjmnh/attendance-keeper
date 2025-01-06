from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ..services.db_service import DatabaseService
from ..models.subject import Subject

bp = Blueprint('subjects', __name__)
db = DatabaseService()

@bp.route('/subjects')
@login_required
def index():
    """List all subjects"""
    if current_user.is_admin():
        subjects = db.list_subjects()
    elif current_user.is_teacher():
        subjects = db.list_subjects(teacher_id=current_user.id)
    else:
        subjects = db.list_subjects(
            class_name=current_user.class_name,
            division=current_user.division
        )
    
    teachers = db.list_users(role='teacher') if current_user.is_admin() else []
    
    return render_template(
        'subjects/index.html',
        subjects=subjects,
        teachers=teachers
    )

@bp.route('/subjects/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new subject"""
    if not current_user.is_admin():
        flash('Unauthorized access', 'error')
        return redirect(url_for('subjects.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        teacher_id = request.form.get('teacher_id')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        description = request.form.get('description')
        
        # Validate required fields
        if not all([name, code, teacher_id, class_name]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('subjects.create'))
        
        # Check if subject code already exists
        existing = db.list_subjects()
        if any(s.code == code for s in existing):
            flash('Subject code already exists', 'error')
            return redirect(url_for('subjects.create'))
        
        # Create subject
        subject = Subject(
            name=name,
            code=code,
            teacher_id=teacher_id,
            class_name=class_name,
            division=division,
            description=description
        )
        
        db.create_subject(subject)
        flash('Subject created successfully', 'success')
        return redirect(url_for('subjects.index'))
    
    teachers = db.list_users(role='teacher')
    return render_template('subjects/create.html', teachers=teachers)

@bp.route('/subjects/<subject_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(subject_id):
    """Edit a subject"""
    if not current_user.is_admin():
        flash('Unauthorized access', 'error')
        return redirect(url_for('subjects.index'))
    
    subject = db.get_subject(subject_id)
    if not subject:
        flash('Subject not found', 'error')
        return redirect(url_for('subjects.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        description = request.form.get('description')
        
        # Validate required fields
        if not all([name, teacher_id, class_name]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('subjects.edit', subject_id=subject_id))
        
        # Update subject
        subject.name = name
        subject.teacher_id = teacher_id
        subject.class_name = class_name
        subject.division = division
        subject.description = description
        
        db.update_subject(subject)
        flash('Subject updated successfully', 'success')
        return redirect(url_for('subjects.index'))
    
    teachers = db.list_users(role='teacher')
    return render_template('subjects/edit.html', subject=subject, teachers=teachers)

@bp.route('/subjects/<subject_id>/delete', methods=['POST'])
@login_required
def delete(subject_id):
    """Delete a subject"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    subject = db.get_subject(subject_id)
    if not subject:
        return jsonify({'error': 'Subject not found'}), 404
    
    try:
        db.delete_subject(subject_id)
        return jsonify({
            'success': True,
            'message': 'Subject deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/subjects/<subject_id>/attendance')
@login_required
def subject_attendance(subject_id):
    """View attendance for a specific subject"""
    subject = db.get_subject(subject_id)
    if not subject:
        flash('Subject not found', 'error')
        return redirect(url_for('subjects.index'))
    
    # Check permissions
    if not current_user.is_admin() and not (
        current_user.is_teacher() and subject.teacher_id == current_user.id
    ):
        flash('Unauthorized access', 'error')
        return redirect(url_for('subjects.index'))
    
    # Get attendance records
    records = db.list_attendance(subject_id=subject_id)
    
    # Get students in this class
    students = db.list_users(
        role='student',
        class_name=subject.class_name,
        division=subject.division
    )
    
    return render_template(
        'subjects/attendance.html',
        subject=subject,
        records=records,
        students=students
    ) 