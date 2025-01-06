from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService

subject = Blueprint('subject', __name__)
db = DatabaseService()

@subject.route('/')
@login_required
def index():
    """
    List all subjects based on user role.
    """
    if current_user.is_student():
        subjects = db.get_student_subjects(current_user.class_name, current_user.division)
    elif current_user.is_teacher():
        subjects = db.get_teacher_subjects(current_user.id)
    else:  # Admin
        subjects = db.get_all_subjects()
    
    return render_template('subject/index.html', subjects=subjects)

@subject.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """
    Create a new subject.
    """
    if not current_user.is_admin():
        flash('Access denied. Administrators only.', 'danger')
        return redirect(url_for('subject.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        teacher_id = request.form.get('teacher_id')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        description = request.form.get('description')
        
        if not all([name, code, teacher_id, class_name, division]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('subject.create'))
        
        # Check if subject code already exists
        if db.get_subject_by_code(code):
            flash('Subject code already exists.', 'danger')
            return redirect(url_for('subject.create'))
        
        # Create subject
        try:
            subject = {
                'name': name,
                'code': code,
                'teacher_id': teacher_id,
                'class_name': class_name,
                'division': division,
                'description': description
            }
            
            subject_id = db.create_subject(subject)
            if subject_id:
                flash('Subject created successfully.', 'success')
                return redirect(url_for('subject.index'))
            
        except Exception as e:
            flash('An error occurred while creating the subject.', 'danger')
            return redirect(url_for('subject.create'))
    
    # Get list of teachers for dropdown
    teachers = db.get_all_teachers()
    return render_template('subject/create.html', teachers=teachers)

@subject.route('/edit/<subject_id>', methods=['GET', 'POST'])
@login_required
def edit(subject_id):
    """
    Edit an existing subject.
    """
    if not current_user.is_admin():
        flash('Access denied. Administrators only.', 'danger')
        return redirect(url_for('subject.index'))
    
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
        return redirect(url_for('subject.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        teacher_id = request.form.get('teacher_id')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        description = request.form.get('description')
        
        if not all([name, code, teacher_id, class_name, division]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('subject.edit', subject_id=subject_id))
        
        # Check if subject code already exists (excluding current subject)
        existing_subject = db.get_subject_by_code(code)
        if existing_subject and existing_subject['id'] != subject_id:
            flash('Subject code already exists.', 'danger')
            return redirect(url_for('subject.edit', subject_id=subject_id))
        
        # Update subject
        try:
            updates = {
                'name': name,
                'code': code,
                'teacher_id': teacher_id,
                'class_name': class_name,
                'division': division,
                'description': description
            }
            
            db.update_subject(subject_id, updates)
            flash('Subject updated successfully.', 'success')
            return redirect(url_for('subject.index'))
            
        except Exception as e:
            flash('An error occurred while updating the subject.', 'danger')
            return redirect(url_for('subject.edit', subject_id=subject_id))
    
    # Get list of teachers for dropdown
    teachers = db.get_all_teachers()
    return render_template('subject/edit.html', subject=subject, teachers=teachers)

@subject.route('/delete/<subject_id>', methods=['DELETE'])
@login_required
def delete(subject_id):
    """
    Delete a subject.
    """
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        # Check if subject exists
        subject = db.get_subject_by_id(subject_id)
        if not subject:
            return jsonify({'success': False, 'message': 'Subject not found'})
        
        # Check if subject has attendance records
        if db.subject_has_attendance(subject_id):
            return jsonify({
                'success': False,
                'message': 'Cannot delete subject with attendance records'
            })
        
        # Delete subject
        db.delete_subject(subject_id)
        return jsonify({
            'success': True,
            'message': 'Subject deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@subject.route('/view/<subject_id>')
@login_required
def view(subject_id):
    """
    View subject details and statistics.
    """
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
        return redirect(url_for('subject.index'))
    
    # Check access permissions
    if current_user.is_student():
        student_subjects = db.get_student_subjects(current_user.class_name, current_user.division)
        if not any(s['id'] == subject_id for s in student_subjects):
            flash('Access denied.', 'danger')
            return redirect(url_for('subject.index'))
    elif current_user.is_teacher() and subject['teacher_id'] != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('subject.index'))
    
    # Get subject statistics
    stats = db.get_attendance_stats_by_subject(subject_id)
    recent_attendance = db.get_recent_attendance_by_subject(subject_id, limit=5)
    
    return render_template('subject/view.html',
                         subject=subject,
                         stats=stats,
                         recent_attendance=recent_attendance) 