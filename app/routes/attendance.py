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
        subject_id = request.args.get('subject_id')
        status = request.args.get('status')
        
        # Base query
        query = current_app.db.collection('attendance')
        
        # Apply date filter
        query = query.where('date', '==', date)
        
        # For teachers, only show their assigned classes
        if current_user.role == 'teacher':
            if not current_user.classes:
                return render_template('attendance/view.html', records=[], subjects=[], date=date,
                                    error="No classes assigned to your account.")
            query = query.where('subject_id', 'in', current_user.classes)
        
        # Apply additional filters if provided
        if subject_id:
            query = query.where('subject_id', '==', subject_id)
        if status:
            query = query.where('status', '==', status)
            
        # Execute query
        records = []
        for doc in query.stream():
            record = doc.to_dict()
            record['id'] = doc.id
            records.append(record)
            
        # Get available subjects for filtering
        subjects = []
        if current_user.role == 'admin':
            # Admin can see all subjects
            subjects_ref = current_app.db.collection('subjects').stream()
            subjects = [{'id': doc.id, 'name': doc.to_dict()['name']} for doc in subjects_ref]
        else:
            # Teachers can only see their assigned subjects
            for class_id in current_user.classes:
                subject_doc = current_app.db.collection('subjects').document(class_id).get()
                if subject_doc.exists:
                    subject_data = subject_doc.to_dict()
                    subjects.append({
                        'id': subject_doc.id,
                        'name': subject_data.get('name', '')
                    })
        
        return render_template('attendance/view.html', records=records, subjects=subjects, date=date)
        
    except Exception as e:
        current_app.logger.error(f"Error viewing attendance: {str(e)}")
        return render_template('attendance/view.html', records=[], subjects=[], date=date,
                             error="An error occurred while fetching attendance records.")

@attendance_bp.route('/mark', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def mark_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        status = data.get('status', 'PRESENT')
        
        if not all([student_id, subject_id]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # For teachers, validate they have access to this class
        if current_user.role == 'teacher' and subject_id not in current_user.classes:
            return jsonify({'error': 'You are not authorized to mark attendance for this class'}), 403
            
        # Check if student exists
        student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
        if not student_ref:
            return jsonify({'error': 'Student not found'}), 404
            
        student_data = student_ref[0].to_dict()
        
        # Create attendance record
        attendance_data = {
            'student_id': student_id,
            'student_name': student_data.get('name', ''),
            'subject_id': subject_id,
            'status': status,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'marked_by': current_user.email
        }
        
        # Add to database
        doc_ref = current_app.db.collection('attendance').add(attendance_data)
        
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
    """Get attendance records with filters"""
    try:
        student_id = request.args.get('student_id')
        subject_id = request.args.get('subject_id')
        date_range = request.args.get('date_range')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        status = request.args.get('status')
        search = request.args.get('search')

        current_app.logger.info(f"Fetching attendance with filters: date_range={date_range}, subject_id={subject_id}, status={status}, search={search}")

        try:
            # Build query
            query = current_app.db.collection('attendance')
            
            # Note: This query requires a composite index on (subject_id, timestamp, __name__)
            # Create the index in Firebase Console or use the link in the error message
            if current_user.role == 'teacher':
                query = query.where('subject_id', 'in', current_user.classes)
                current_app.logger.debug(f"Applied teacher filter: classes={current_user.classes}")
            elif current_user.role == 'student':
                query = query.where('student_id', '==', current_user.id)
                current_app.logger.debug(f"Applied student filter: student_id={current_user.id}")

            # Apply filters
            if student_id:
                query = query.where('student_id', '==', student_id)
            if subject_id:
                query = query.where('subject_id', '==', subject_id)
            if status:
                query = query.where('status', '==', status)

            # Date range filter
            today = datetime.now().date()
            if date_range == 'today':
                query = query.where('timestamp', '>=', today.isoformat())
                query = query.where('timestamp', '<', (today + timedelta(days=1)).isoformat())
                current_app.logger.debug(f"Applied today filter: {today.isoformat()} to {(today + timedelta(days=1)).isoformat()}")
            elif date_range == 'week':
                start_of_week = today - timedelta(days=today.weekday())
                query = query.where('timestamp', '>=', start_of_week.isoformat())
                query = query.where('timestamp', '<', (start_of_week + timedelta(days=7)).isoformat())
                current_app.logger.debug(f"Applied week filter: {start_of_week.isoformat()} to {(start_of_week + timedelta(days=7)).isoformat()}")
            elif date_range == 'month':
                start_of_month = today.replace(day=1)
                if today.month == 12:
                    end_of_month = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    end_of_month = today.replace(month=today.month + 1, day=1)
                query = query.where('timestamp', '>=', start_of_month.isoformat())
                query = query.where('timestamp', '<', end_of_month.isoformat())
                current_app.logger.debug(f"Applied month filter: {start_of_month.isoformat()} to {end_of_month.isoformat()}")
            elif date_range == 'custom' and date_from and date_to:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').date() + timedelta(days=1)
                    query = query.where('timestamp', '>=', from_date.isoformat())
                    query = query.where('timestamp', '<', to_date.isoformat())
                    current_app.logger.debug(f"Applied custom date filter: {from_date.isoformat()} to {to_date.isoformat()}")
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            elif date_range != 'all':  # Only apply default today filter if not 'all'
                # Default to today if no valid date range is specified
                query = query.where('timestamp', '>=', today.isoformat())
                query = query.where('timestamp', '<', (today + timedelta(days=1)).isoformat())
                current_app.logger.debug(f"No date range specified, defaulting to today: {today.isoformat()} to {(today + timedelta(days=1)).isoformat()}")

            # Always order by timestamp descending for consistent ordering
            query = query.order_by('timestamp', direction='DESCENDING')
            
            # For 'all' option, limit to last 1000 records to prevent performance issues
            if date_range == 'all':
                query = query.limit(1000)
                current_app.logger.debug("Showing all records (limited to 1000)")

            # Execute query and format results
            records = []
            docs = list(query.stream())  # Convert to list to get count
            current_app.logger.info(f"Found {len(docs)} records before search filter")

            for doc in docs:
                record = doc.to_dict()
                record['doc_id'] = doc.id
                
                # Apply search filter if provided
                if search:
                    search = search.lower()
                    if search not in record.get('name', '').lower() and search not in record.get('student_id', '').lower():
                        continue
                
                # Format timestamp
                timestamp = record.get('timestamp')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        record['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        record['timestamp'] = timestamp
                
                records.append(record)
            
            current_app.logger.info(f"Returning {len(records)} records after all filters")
            return jsonify(records)
        except Exception as e:
            if "The query requires an index" in str(e):
                current_app.logger.error(f"Missing Firestore index: {str(e)}")
                # Extract the index creation URL from the error message
                error_msg = str(e)
                index_url_start = error_msg.find("https://console.firebase.google.com")
                if index_url_start != -1:
                    index_url = error_msg[index_url_start:].split(" ")[0]
                    return jsonify({
                        'error': 'Database index needs to be created. Please contact the administrator.',
                        'admin_message': f'Create the required index at: {index_url}'
                    }), 400
            raise  # Re-raise other exceptions
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

