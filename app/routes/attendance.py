from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pandas as pd
import io
from app.utils.decorators import role_required

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@bp.route('/')
@login_required
def index():
    """Attendance management view"""
    # Get subjects for teachers and admins
    subjects = []
    if current_user.role in ['admin', 'teacher']:
        subjects_ref = current_app.db.collection('subjects').stream()
        subjects = [{
            'id': doc.id,
            'name': doc.to_dict().get('name', '')
        } for doc in subjects_ref]
    
    return render_template('attendance/manage.html', subjects=subjects)

@bp.route('/api/attendance')
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

        # Build query
        query = current_app.db.collection('attendance')
        
        # Apply role-based restrictions
        if current_user.role == 'teacher':
            query = query.where('subject_id', 'in', current_user.classes)
        elif current_user.role == 'student':
            query = query.where('student_id', '==', current_user.id)

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
        elif date_range == 'week':
            start_of_week = today - timedelta(days=today.weekday())
            query = query.where('timestamp', '>=', start_of_week.isoformat())
            query = query.where('timestamp', '<', (start_of_week + timedelta(days=7)).isoformat())
        elif date_range == 'month':
            start_of_month = today.replace(day=1)
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1)
            query = query.where('timestamp', '>=', start_of_month.isoformat())
            query = query.where('timestamp', '<', end_of_month.isoformat())
        elif date_range == 'custom' and date_from and date_to:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date() + timedelta(days=1)
                query = query.where('timestamp', '>=', from_date.isoformat())
                query = query.where('timestamp', '<', to_date.isoformat())
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Order by timestamp descending
        query = query.order_by('timestamp', direction='DESCENDING')

        # Execute query and format results
        records = []
        for doc in query.stream():
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
        
        return jsonify(records)
    except Exception as e:
        current_app.logger.error(f"Error getting attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/attendance/update', methods=['POST'])
@role_required(['admin', 'teacher'])
def update_attendance():
    """Update attendance records"""
    try:
        data = request.get_json()
        records = data.get('records', [])
        
        for record in records:
            doc_id = record.get('doc_id')
            if not doc_id:
                continue
                
            # Verify permissions
            doc_ref = current_app.db.collection('attendance').document(doc_id)
            doc = doc_ref.get()
            if not doc.exists:
                continue
                
            doc_data = doc.to_dict()
            if current_user.role == 'teacher' and doc_data.get('subject_id') not in current_user.classes:
                continue
            
            # Update record
            update_data = {
                'name': record.get('name'),
                'status': record.get('status'),
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.id
            }
            doc_ref.update(update_data)
        
        return jsonify({'message': 'Records updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/attendance/<doc_id>', methods=['DELETE'])
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

@bp.route('/api/attendance/template')
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

@bp.route('/api/attendance/export')
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

@bp.route('/api/attendance/upload', methods=['POST'])
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

@bp.route('/view')
@login_required
def view_attendance():
    """View attendance records"""
    # Get subjects for teachers and admins
    subjects = []
    if current_user.role in ['admin', 'teacher']:
        subjects_ref = current_app.db.collection('subjects').stream()
        subjects = [{
            'id': doc.id,
            'name': doc.to_dict().get('name', '')
        } for doc in subjects_ref]
    
    return render_template('attendance/view.html', subjects=subjects)
