from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Initialize default stats and data
    stats = {
        'total_students': 0,
        'total_subjects': 0,
        'today_attendance': 0,
        'attendance_trend': 'No change'
    }
    
    attendance_data = {
        'labels': [],
        'values': []
    }
    
    try:
        # Get date range for attendance data
        today = datetime.now().date()
        start_date = today - timedelta(days=7)  # Last 7 days
        today_str = today.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        # Get total students count
        students_query = current_app.db.collection('users').where('role', '==', 'student')
        
        # For teachers, we need to filter by their assigned classes
        teacher_classes = []
        if current_user.role == 'teacher':
            teacher_classes = getattr(current_user, 'classes', [])
            if not teacher_classes:
                return render_template('dashboard.html',
                                    stats=stats,
                                    attendance_data=attendance_data,
                                    attendance_records=[],
                                    error="No classes assigned to your account.")
            
            # For teachers, we'll filter after getting the documents
            students = list(students_query.stream())
            stats['total_students'] = sum(1 for doc in students 
                if f"{doc.to_dict().get('class')}-{doc.to_dict().get('division')}" in teacher_classes)
        elif current_user.role == 'student':
            stats['total_students'] = 1  # Only themselves
        else:
            stats['total_students'] = len(list(students_query.stream()))
        
        # Get total subjects count
        subjects_query = current_app.db.collection('subjects')
        if current_user.role == 'teacher':
            # For teachers, only count subjects they teach
            subjects = list(subjects_query.stream())
            stats['total_subjects'] = sum(1 for s in subjects 
                if f"{s.to_dict().get('class')}-{s.to_dict().get('division')}" in teacher_classes)
        elif current_user.role == 'student':
            # For students, count subjects in their class
            class_id = f"{getattr(current_user, 'class_id', '')}-{getattr(current_user, 'division', '')}"
            subjects = list(subjects_query.stream())
            stats['total_subjects'] = sum(1 for s in subjects 
                if f"{s.to_dict().get('class')}-{s.to_dict().get('division')}" == class_id)
        else:
            stats['total_subjects'] = len(list(subjects_query.stream()))
        
        # Initialize query for attendance
        attendance_query = current_app.db.collection('attendance')
        
        # Add date range filters
        attendance_query = attendance_query.where('date', '>=', start_date_str)
        attendance_query = attendance_query.where('date', '<=', today_str)
        
        # For students, only show their own attendance
        if current_user.role == 'student':
            attendance_query = attendance_query.where('student_id', '==', current_user.id)
        
        # Execute query
        attendance_docs = list(attendance_query.stream())
        
        # Process attendance records
        daily_attendance = {}
        total_students = {}
        
        for doc in attendance_docs:
            record = doc.to_dict()
            date = record.get('date')
            status = record.get('status')
            
            # Skip if date is missing
            if not date:
                continue
            
            # For teachers, filter by their assigned classes
            if current_user.role == 'teacher':
                student_class = f"{record.get('class')}-{record.get('division')}"
                if student_class not in teacher_classes:
                    continue
            
            # Initialize counters for this date
            if date not in daily_attendance:
                daily_attendance[date] = {'present': 0, 'total': 0}
            if date not in total_students:
                total_students[date] = set()
            
            # Count attendance
            student_id = record.get('student_id')
            if student_id:
                total_students[date].add(student_id)
                if status == 'PRESENT':
                    daily_attendance[date]['present'] += 1
        
        # Calculate today's attendance percentage
        if today_str in daily_attendance and total_students.get(today_str):
            total = len(total_students[today_str])
            present = daily_attendance[today_str]['present']
            stats['today_attendance'] = round((present / total * 100) if total > 0 else 0)
        
        # Calculate attendance trend
        if len(daily_attendance) >= 2:
            dates = sorted(daily_attendance.keys())
            today_percent = (daily_attendance[dates[-1]]['present'] / len(total_students[dates[-1]])) * 100 if dates[-1] in total_students and len(total_students[dates[-1]]) > 0 else 0
            yesterday_percent = (daily_attendance[dates[-2]]['present'] / len(total_students[dates[-2]])) * 100 if dates[-2] in total_students and len(total_students[dates[-2]]) > 0 else 0
            diff = today_percent - yesterday_percent
            if diff > 0:
                stats['attendance_trend'] = f"↑ {abs(round(diff))}% increase"
            elif diff < 0:
                stats['attendance_trend'] = f"↓ {abs(round(diff))}% decrease"
        
        # Calculate attendance percentage for each day
        for date in sorted(daily_attendance.keys()):
            attendance_data['labels'].append(str(date))
            total = len(total_students[date])
            present = daily_attendance[date]['present']
            percentage = round((present / total * 100) if total > 0 else 0, 2)
            attendance_data['values'].append(float(percentage))
        
        # Get recent attendance records
        recent_query = current_app.db.collection('attendance').order_by('timestamp', direction='DESCENDING').limit(5)
        recent_records = []
        
        for doc in recent_query.stream():
            record = doc.to_dict()
            
            # For teachers, filter by their assigned classes
            if current_user.role == 'teacher':
                student_class = f"{record.get('class')}-{record.get('division')}"
                if student_class not in teacher_classes:
                    continue
            
            # Get student name from either student_name or name field
            name = record.get('student_name') or record.get('name')
            if not name:
                # Try to fetch student name from users collection
                student_id = record.get('student_id')
                if student_id:
                    student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
                    if student_ref:
                        student_data = student_ref[0].to_dict()
                        name = student_data.get('name', 'Unknown')
                    else:
                        name = 'Unknown'
                else:
                    name = 'Unknown'
            
            # Convert record values to JSON serializable types
            recent_records.append({
                'name': str(name),
                'class': str(record.get('class', '')),
                'division': str(record.get('division', '')),
                'timestamp': str(record.get('timestamp', '')),
                'status': str(record.get('status', 'UNKNOWN')),
                'subject_name': str(record.get('subject_name', ''))
            })
        
        return render_template('dashboard.html',
                            stats=stats,
                            attendance_data=attendance_data,
                            attendance_records=recent_records)
                            
    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard.html',
                            stats=stats,
                            attendance_data=attendance_data,
                            attendance_records=[])