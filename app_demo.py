from flask import Flask, render_template, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import numpy as np
import os
import json
from datetime import datetime, time
import threading
import schedule
import time as time_module
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'eduguard_demo_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eduguard_demo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/student_photos'

db = SQLAlchemy(app)

# Global variables (simplified for demo)
monitoring_active = False

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    photo_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_monitoring_period = db.Column(db.Boolean, default=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    detected_at = db.Column(db.DateTime)
    
    student = db.relationship('Student', backref='attendances')
    time_slot = db.relationship('TimeSlot', backref='attendances')

class SpecialPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    reason = db.Column(db.String(200))
    approved_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='permissions')
    time_slot = db.relationship('TimeSlot', backref='permissions')

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    
    student = db.relationship('Student', backref='alerts')
    time_slot = db.relationship('TimeSlot', backref='alerts')

class Official(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50))

# Helper Functions
def get_current_time_slot():
    current_time = datetime.now().time()
    time_slot = TimeSlot.query.filter(
        TimeSlot.start_time <= current_time,
        TimeSlot.end_time >= current_time
    ).first()
    return time_slot

def create_demo_alert(student_id, message):
    """Create a demo alert for testing purposes"""
    current_time_slot = get_current_time_slot()
    alert = Alert(
        student_id=student_id,
        alert_type='unauthorized_presence',
        message=message,
        time_slot_id=current_time_slot.id if current_time_slot else None
    )
    db.session.add(alert)
    db.session.commit()
    return alert

# Demo camera feed (placeholder image)
def generate_demo_frames():
    """Generate demo camera frames"""
    placeholder = create_placeholder_image()
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
        time_module.sleep(0.1)

def create_placeholder_image():
    """Create a simple placeholder image for demo"""
    # Simple JPEG placeholder
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x01\x90\x02\x80\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1c\x00\x00\x02\x03\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x05\x02\x06\x01\x03\x07\x08\xff\xc4\x00:\x10\x00\x01\x04\x02\x01\x04\x02\x04\x03\x05\x06\x07\x08\x01\x00\x02\x03\x04\x11\x05\x12!1A\x06\x13Qaq\x14"2\x81\x91\xa1\x07#B\xb1\xc1\xd1\xf0$3Rr\x82\x92\xb2\xf1\x15CS\xc2\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf4\x9f\x91\x8a(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00\xff\xd9'

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    students_count = Student.query.count()
    alerts_today = Alert.query.filter(Alert.created_at >= datetime.combine(datetime.now().date(), time.min)).count()
    current_time_slot = get_current_time_slot()
    
    return render_template('dashboard.html', 
                         students_count=students_count,
                         alerts_today=alerts_today,
                         current_time_slot=current_time_slot)

@app.route('/video_feed')
def video_feed():
    return Response(generate_demo_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/students')
def students():
    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        
        student = Student(
            student_id=data['student_id'],
            name=data['name'],
            email=data['email']
        )
        
        if 'photo' in data:
            photo_data = data['photo'].split(',')[1]
            photo_bytes = base64.b64decode(photo_data)
            
            filename = secure_filename(f"{data['student_id']}.jpg")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(photo_path, 'wb') as f:
                f.write(photo_bytes)
            
            student.photo_path = photo_path
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Student added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/time_slots')
def time_slots():
    slots = TimeSlot.query.all()
    return render_template('time_slots.html', slots=slots)

@app.route('/add_time_slot', methods=['POST'])
def add_time_slot():
    try:
        data = request.get_json()
        
        slot = TimeSlot(
            name=data['name'],
            start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
            end_time=datetime.strptime(data['end_time'], '%H:%M').time(),
            is_monitoring_period=data.get('is_monitoring_period', True)
        )
        
        db.session.add(slot)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Time slot added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/attendance')
def attendance():
    today = datetime.now().date()
    attendances = db.session.query(Attendance, Student, TimeSlot).join(
        Student, Attendance.student_id == Student.student_id
    ).join(
        TimeSlot, Attendance.time_slot_id == TimeSlot.id
    ).filter(Attendance.date == today).all()
    
    return render_template('attendance.html', attendances=attendances, date=today)

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    try:
        data = request.get_json()
        today = datetime.now().date()
        
        existing = Attendance.query.filter_by(
            student_id=data['student_id'],
            date=today,
            time_slot_id=data['time_slot_id']
        ).first()
        
        if existing:
            existing.status = data['status']
            existing.detected_at = datetime.now() if data['status'] == 'present' else None
        else:
            attendance = Attendance(
                student_id=data['student_id'],
                date=today,
                time_slot_id=data['time_slot_id'],
                status=data['status'],
                detected_at=datetime.now() if data['status'] == 'present' else None
            )
            db.session.add(attendance)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Attendance marked successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/permissions')
def permissions():
    permissions = db.session.query(SpecialPermission, Student, TimeSlot).join(
        Student, SpecialPermission.student_id == Student.student_id
    ).join(
        TimeSlot, SpecialPermission.time_slot_id == TimeSlot.id
    ).all()
    
    return render_template('permissions.html', permissions=permissions)

@app.route('/add_permission', methods=['POST'])
def add_permission():
    try:
        data = request.get_json()
        
        permission = SpecialPermission(
            student_id=data['student_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            time_slot_id=data['time_slot_id'],
            reason=data['reason'],
            approved_by=data['approved_by']
        )
        
        db.session.add(permission)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Permission added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/alerts')
def alerts():
    alerts = db.session.query(Alert, Student, TimeSlot).join(
        Student, Alert.student_id == Student.student_id
    ).join(
        TimeSlot, Alert.time_slot_id == TimeSlot.id
    ).order_by(Alert.created_at.desc()).all()
    
    return render_template('alerts.html', alerts=alerts)

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global monitoring_active
    monitoring_active = True
    return jsonify({'success': True, 'message': 'Monitoring started (Demo Mode)'})

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    return jsonify({'success': True, 'message': 'Monitoring stopped'})

@app.route('/officials')
def officials():
    officials = Official.query.all()
    return render_template('officials.html', officials=officials)

@app.route('/add_official', methods=['POST'])
def add_official():
    try:
        data = request.get_json()
        
        official = Official(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone'),
            role=data.get('role')
        )
        
        db.session.add(official)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Official added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Demo functionality
@app.route('/create_demo_alert', methods=['POST'])
def create_demo_alert_route():
    """Create a demo alert for testing"""
    try:
        # Get first student for demo
        student = Student.query.first()
        if not student:
            return jsonify({'success': False, 'message': 'No students found. Add a student first.'})
        
        message = f"DEMO: Student {student.name} ({student.student_id}) detected during unauthorized time"
        alert = create_demo_alert(student.student_id, message)
        
        return jsonify({'success': True, 'message': 'Demo alert created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API endpoints for the frontend
@app.route('/api/students')
def api_students():
    students = Student.query.all()
    return jsonify({
        'students': [{
            'student_id': s.student_id,
            'name': s.name,
            'email': s.email
        } for s in students]
    })

@app.route('/api/time_slots')
def api_time_slots():
    time_slots = TimeSlot.query.all()
    return jsonify({
        'time_slots': [{
            'id': ts.id,
            'name': ts.name,
            'start_time': ts.start_time.strftime('%H:%M'),
            'end_time': ts.end_time.strftime('%H:%M'),
            'is_monitoring_period': ts.is_monitoring_period
        } for ts in time_slots]
    })

@app.route('/api/recent_alerts')
def api_recent_alerts():
    alerts = db.session.query(Alert, Student).join(
        Student, Alert.student_id == Student.student_id
    ).order_by(Alert.created_at.desc()).limit(5).all()
    
    return jsonify({
        'alerts': [{
            'student_name': student.name,
            'message': alert.message,
            'time': alert.created_at.strftime('%H:%M')
        } for alert, student in alerts]
    })

@app.route('/api/attendance_stats')
def api_attendance_stats():
    today = datetime.now().date()
    attendances = Attendance.query.filter_by(date=today).all()
    
    present = len([a for a in attendances if a.status == 'present'])
    absent = len([a for a in attendances if a.status == 'absent'])
    late = len([a for a in attendances if a.status == 'late'])
    
    return jsonify({
        'present': present,
        'absent': absent,
        'late': late
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("EDUGUARD Demo started successfully!")
        print("🛡️  Camera: Demo mode (placeholder feed)")
        print("🔍  Face Recognition: Manual mode only")
        print("📊  Database: SQLite (demo)")
        print("🌐  Access: http://localhost:5000")
        print("\n📝  Demo Features Available:")
        print("   - Student Management")
        print("   - Time Slot Configuration") 
        print("   - Manual Attendance Tracking")
        print("   - Special Permissions")
        print("   - Alert Management")
        print("   - Officials Management")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)