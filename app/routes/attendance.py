from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pandas as pd
import io
from app.utils.decorators import role_required
from app.services.db_service import DatabaseService
from app.services.rekognition_service import RekognitionService

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/view')
@login_required
def view_attendance():
    try:
        # Get filter parameters
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Base query
        query = current_app.db.collection('attendance')
        
        # Apply date filter
        query = query.where('date', '==', date)
        
        # For students, only show their own records
        if current_user.role == 'student':
            query = query.where('student_id', '==', current_user.student_id)
            
        # Order by timestamp to get latest records first
        query = query.order_by('timestamp', direction='DESCENDING')
            
        # Execute query
        latest_records = {}  # Dictionary to store latest record per student
        for doc in query.stream():
            record = doc.to_dict()
            record['doc_id'] = doc.id
            
            # For teachers, only show their assigned classes
            if current_user.role == 'teacher':
                if not hasattr(current_user, 'classes') or not current_user.classes:
                    current_app.logger.warning(f"Teacher {current_user.email} has no assigned classes")
                    continue
                    
                class_division = f"{record.get('class', '')}-{record.get('division', '')}"
                if class_division not in current_user.classes:
                    continue
            
            # Only keep the latest record for each student (first one due to descending order)
            student_id = record.get('student_id')
            if student_id not in latest_records:
                latest_records[student_id] = record
            
        # Convert dictionary to list
        records = list(latest_records.values())
            
        # Sort records by status (PRESENT first) and then by student name
        records.sort(key=lambda x: (x.get('status') != 'PRESENT', x.get('student_name', '')))
        
        current_app.logger.info(f"Found {len(records)} unique attendance records for date {date}")
        return render_template('attendance/view.html', 
                             records=records, 
                             date=date,
                             user_role=current_user.role)
                             
    except Exception as e:
        current_app.logger.error(f"Error viewing attendance: {str(e)}")
        return render_template('attendance/view.html', 
                             records=[], 
                             date=date,
                             user_role=current_user.role,
                             error="An error occurred while fetching attendance records.")

@attendance_bp.route('/mark', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def mark_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        status = data.get('status', 'PRESENT')
        
        if not student_id:
            return jsonify({'error': 'Student ID is required'}), 400
            
        # Get student details
        student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
        if not student_ref:
            return jsonify({'error': 'Student not found'}), 404
            
        student_data = student_ref[0].to_dict()
        student_class = student_data.get('class', '')
        student_division = student_data.get('division', '')
        class_division = f"{student_class}-{student_division}"
            
        # For teachers, validate they have access to this student's class
        if current_user.role == 'teacher':
            if not hasattr(current_user, 'classes') or not current_user.classes:
                current_app.logger.warning(f"Teacher {current_user.email} has no assigned classes")
                return jsonify({'error': 'No classes assigned to your account'}), 403
                
            if class_division not in current_user.classes:
                current_app.logger.warning(f"Teacher {current_user.email} attempted to mark attendance for unauthorized class {class_division}")
                return jsonify({'error': 'You are not authorized to mark attendance for this student'}), 403
            
        # Create attendance record
        attendance_data = {
            'student_id': student_id,
            'student_name': student_data.get('name', ''),
            'class': student_class,
            'division': student_division,
            'status': status,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'marked_by': current_user.email
        }
        
        # Check if attendance already exists for today
        today = datetime.now().strftime('%Y-%m-%d')
        existing_attendance = current_app.db.collection('attendance').where(
            'student_id', '==', student_id
        ).where('date', '==', today).get()
        
        if existing_attendance:
            # Update existing attendance
            doc = existing_attendance[0]
            doc.reference.update({
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'marked_by': current_user.email
            })
            current_app.logger.info(f"Updated attendance for student {student_id} in class {class_division}")
            return jsonify({
                'message': 'Attendance updated successfully',
                'id': doc.id
            }), 200
        else:
            # Add new attendance record
            doc_ref = current_app.db.collection('attendance').add(attendance_data)
            current_app.logger.info(f"Marked new attendance for student {student_id} in class {class_division}")
            return jsonify({
                'message': 'Attendance marked successfully',
                'id': doc_ref[1].id
            }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error marking attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/update/<record_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'teacher'])
def update_attendance(record_id):
    try:
        data = request.json
        status = data.get('status')
        
        if not status:
            return jsonify({'error': 'Status is required'}), 400
            
        # Get the attendance record
        record_ref = current_app.db.collection('attendance').document(record_id)
        record = record_ref.get()
        
        if not record.exists:
            return jsonify({'error': 'Attendance record not found'}), 404
            
        record_data = record.to_dict()
        
        # For teachers, validate they have access to this class
        if current_user.role == 'teacher' and record_data['subject_id'] not in current_user.classes:
            return jsonify({'error': 'You are not authorized to update attendance for this class'}), 403
            
        # Update the record
        record_ref.update({
            'status': status,
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        })
        
        return jsonify({'message': 'Attendance updated successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/api/attendance')
@login_required
def get_attendance():
    try:
        # Get filter parameters
        date_range = request.args.get('date_range', 'today')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        status = request.args.get('status')
        search = request.args.get('search', '').lower()
        
        # Base query
        query = current_app.db.collection('attendance')
        
        # Apply date filters
        today = datetime.now().strftime('%Y-%m-%d')
        if date_range == 'today':
            query = query.where('date', '==', today)
        elif date_range == 'week':
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            query = query.where('date', '>=', week_ago)
        elif date_range == 'month':
            month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            query = query.where('date', '>=', month_ago)
        elif date_range == 'custom' and date_from and date_to:
            query = query.where('date', '>=', date_from)
            query = query.where('date', '<=', date_to)
            
        # For students, only show their own records
        if current_user.role == 'student':
            query = query.where('student_id', '==', current_user.student_id)
            
        # Always order by date and timestamp
        query = query.order_by('date', direction='DESCENDING')
        query = query.order_by('timestamp', direction='DESCENDING')
        
        # Execute query and format results
        latest_records = {}  # Dictionary to store latest record per student per date
        docs = list(query.stream())
        current_app.logger.info(f"Found {len(docs)} records before filtering")

        for doc in docs:
            record = doc.to_dict()
            record['doc_id'] = doc.id
            
            # For teachers, only show their assigned classes
            if current_user.role == 'teacher':
                if not hasattr(current_user, 'classes') or not current_user.classes:
                    current_app.logger.warning(f"Teacher {current_user.email} has no assigned classes")
                    continue
                    
                class_division = f"{record.get('class', '')}-{record.get('division', '')}"
                if class_division not in current_user.classes:
                    continue
            
            # Apply status filter if specified
            if status and record.get('status') != status:
                continue
                
            # Apply search filter if specified
            if search:
                student_name = record.get('student_name', '').lower()
                student_id = str(record.get('student_id', '')).lower()
                if search not in student_name and search not in student_id:
                    continue
            
            # Only keep the latest record for each student for each date
            key = f"{record['student_id']}_{record['date']}"
            if key not in latest_records:
                latest_records[key] = record
        
        # Convert dictionary to list and sort
        records = list(latest_records.values())
        records.sort(key=lambda x: (x['date'], x.get('student_name', '')), reverse=True)
        
        current_app.logger.info(f"Returning {len(records)} records after all filters")
        return jsonify(records)
        
    except Exception as e:
        current_app.logger.error(f"Error getting attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/api/attendance/update', methods=['POST'])
@role_required(['admin', 'teacher'])
def bulk_update_attendance():
    """Update attendance record"""
    try:
        data = request.get_json()
        doc_id = data.pop('doc_id', None)  # Remove doc_id and get its value
        
        if not doc_id:
            return jsonify({'error': 'Missing doc_id'}), 400
                
        # Verify permissions
        doc_ref = current_app.db.collection('attendance').document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'error': 'Record not found'}), 404
                
        doc_data = doc.to_dict()
        if current_user.role == 'teacher':
            # Teachers can only update status
            if set(data.keys()) - {'status'}:
                return jsonify({'error': 'Teachers can only update attendance status'}), 403
            if doc_data.get('subject_id') not in current_user.classes:
                return jsonify({'error': 'Unauthorized to update this record'}), 403
            
        # Add metadata
        data.update({
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.id
        })
        
        # Update record
        doc_ref.update(data)
        return jsonify({'message': 'Record updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/api/attendance/<doc_id>', methods=['DELETE'])
@role_required(['admin'])
def delete_attendance(doc_id):
    """Delete an attendance record"""
    try:
        doc_ref = current_app.db.collection('attendance').document(doc_id)
        doc_ref.delete()
        return jsonify({'message': 'Record deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error deleting attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500
@attendance_bp.route('/api/attendance/template')
@role_required(['admin', 'teacher'])
def download_template():
    """Download Excel template for attendance upload"""
    df = pd.DataFrame(columns=[
        'student_id',
        'name',
        'subject_id',
        'subject_name',
        'timestamp',
        'status'
    ])
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='attendance_template.xlsx'
    )

@attendance_bp.route('/api/attendance/export')
@login_required
def export_attendance():
    """Export attendance records to Excel"""
    # Reuse get_attendance logic to get filtered records
    response = get_attendance()
    if isinstance(response, tuple):
        return response
    
    records = response.get_json()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='attendance_export.xlsx'
    )

@attendance_bp.route('/api/attendance/upload', methods=['POST'])
@role_required(['admin', 'teacher'])
def upload_attendance():
    """Upload attendance records from Excel"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Invalid file format. Please upload an Excel file'}), 400
    
    try:
        # Read Excel file
        df = pd.read_excel(file)
        
        # Validate columns
        required_columns = ['student_id', 'name', 'subject_id', 'subject_name', 'timestamp', 'status']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Invalid template format. Please use the provided template'}), 400
        
        # Process records
        records = df.to_dict('records')
        for record in records:
            # Verify teacher permissions
            if current_user.role == 'teacher' and record['subject_id'] not in current_user.classes:
                continue
            
            # Add record
            current_app.db.collection('attendance').add(record)
        
        return jsonify({'message': 'Records uploaded successfully'})
    except Exception as e:
        current_app.logger.error(f"Error uploading attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@attendance_bp.route('/register_student', methods=['POST'])
@login_required
@role_required(['teacher'])
def register_student():
    data = request.form
    student_id = data.get('student_id')
    name = data.get('name')
    subject_id = data.get('subject_id')
    image = request.files.get('image')

    # Validate subject assignment
    user_classes = current_user.classes
    if subject_id not in user_classes:
        return jsonify({'error': 'Unauthorized to register students for this class.'}), 403

    # Proceed with registration logic
    db_service = DatabaseService()
    student = db_service.get_student_by_id(student_id)
    if not student:
        return jsonify({'error': 'Student does not exist.'}), 400

    # Upload image to AWS S3 and register with AWS Rekognition
    rekognition_service = RekognitionService()
    image_url = rekognition_service.upload_image_to_s3(image, student_id)
    rekognition_service.register_face(student_id, image_url)

    # Update Firestore
    db_service.register_student(student_id, name, subject_id, image_url)

    return jsonify({'message': 'Student registered successfully.'}), 201

@attendance_bp.route('/api/attendance/<doc_id>/status', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_attendance_status(doc_id):
    """Update attendance status"""
    try:
        data = request.json
        new_status = data.get('status')
        
        if not new_status or new_status not in ['PRESENT', 'ABSENT']:
            return jsonify({'error': 'Invalid status provided'}), 400
            
        # Get the attendance document
        doc_ref = current_app.db.collection('attendance').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'Attendance record not found'}), 404
            
        # Update the status
        doc_ref.update({
            'status': new_status,
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        })
        
        return jsonify({'message': 'Status updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error updating attendance status: {str(e)}")
        return jsonify({'error': 'Failed to update attendance status'}), 500

