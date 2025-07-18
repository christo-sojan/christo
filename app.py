from flask import Flask, render_template, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import numpy as np
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV not available. Camera functionality disabled.")

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: Face recognition not available. Manual attendance only.")
import os
import json
from datetime import datetime, time
import threading
import schedule
import time as time_module
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'eduguard_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eduguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/student_photos'

db = SQLAlchemy(app)

# Global variables
camera = None
known_face_encodings = []
known_face_names = []
monitoring_active = False
current_session = None

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    photo_path = db.Column(db.String(200))
    face_encoding = db.Column(db.Text)  # Store face encoding as JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Period 1", "Break", etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_monitoring_period = db.Column(db.Boolean, default=True)  # False for breaks/intervals

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # present, absent, late
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
    alert_type = db.Column(db.String(50), nullable=False)  # unauthorized_presence, late_arrival
    message = db.Column(db.Text, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, sent, acknowledged
    
    student = db.relationship('Student', backref='alerts')
    time_slot = db.relationship('TimeSlot', backref='alerts')

class Official(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50))  # principal, dean, hod, etc.

# Camera and Face Recognition Functions
def initialize_camera():
    global camera
    if not OPENCV_AVAILABLE:
        print("Camera initialization skipped - OpenCV not available")
        return False
    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Warning: Could not open camera")
        return camera is not None and camera.isOpened()
    except Exception as e:
        print(f"Error initializing camera: {e}")
        return False

def load_known_faces():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    if not FACE_RECOGNITION_AVAILABLE:
        print("Face recognition disabled - models not available")
        return
    
    students = Student.query.all()
    for student in students:
        if student.face_encoding:
            try:
                encoding = np.array(json.loads(student.face_encoding))
                known_face_encodings.append(encoding)
                known_face_names.append(student.student_id)
            except Exception as e:
                print(f"Error loading face encoding for {student.name}: {e}")

def detect_faces_in_frame(frame):
    if not FACE_RECOGNITION_AVAILABLE or not OPENCV_AVAILABLE:
        return [], []
        
    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    # Find faces in frame
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    
    detected_students = []
    
    for face_encoding in face_encodings:
        # Compare with known faces
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                student_id = known_face_names[best_match_index]
                detected_students.append(student_id)
    
    return detected_students, face_locations

def get_current_time_slot():
    current_time = datetime.now().time()
    time_slot = TimeSlot.query.filter(
        TimeSlot.start_time <= current_time,
        TimeSlot.end_time >= current_time
    ).first()
    return time_slot

def check_unauthorized_presence(detected_students):
    current_time_slot = get_current_time_slot()
    if not current_time_slot or not current_time_slot.is_monitoring_period:
        return
    
    today = datetime.now().date()
    alerts_created = []
    
    for student_id in detected_students:
        # Check if student is marked absent
        attendance = Attendance.query.filter_by(
            student_id=student_id,
            date=today,
            time_slot_id=current_time_slot.id
        ).first()
        
        # Check if student has special permission
        permission = SpecialPermission.query.filter_by(
            student_id=student_id,
            date=today,
            time_slot_id=current_time_slot.id
        ).first()
        
        # If student is marked absent and doesn't have permission, create alert
        if attendance and attendance.status == 'absent' and not permission:
            student = Student.query.filter_by(student_id=student_id).first()
            
            # Check if alert already exists for today
            existing_alert = Alert.query.filter_by(
                student_id=student_id,
                time_slot_id=current_time_slot.id,
                alert_type='unauthorized_presence'
            ).filter(Alert.created_at >= datetime.combine(today, time.min)).first()
            
            if not existing_alert:
                alert = Alert(
                    student_id=student_id,
                    alert_type='unauthorized_presence',
                    message=f"Student {student.name} ({student_id}) detected in campus during {current_time_slot.name} but marked absent",
                    time_slot_id=current_time_slot.id
                )
                db.session.add(alert)
                alerts_created.append(alert)
    
    if alerts_created:
        db.session.commit()
        # Send notifications for new alerts
        for alert in alerts_created:
            send_alert_notification(alert)

def send_alert_notification(alert):
    try:
        officials = Official.query.all()
        for official in officials:
            # Here you would implement email/SMS sending
            # For demo, we'll just print
            print(f"ALERT: Sending to {official.name} ({official.email}): {alert.message}")
    except Exception as e:
        print(f"Error sending alert notification: {e}")

# Camera streaming
def generate_frames():
    global camera, monitoring_active
    
    if not OPENCV_AVAILABLE:
        # Return a placeholder image when camera is not available
        placeholder = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x01\x90\x02\x80\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1c\x00\x00\x02\x03\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x05\x02\x06\x01\x03\x07\x08\xff\xc4\x00:\x10\x00\x01\x04\x02\x01\x04\x02\x04\x03\x05\x06\x07\x08\x01\x00\x02\x03\x04\x11\x05\x12!1A\x06\x13Qaq\x14"2\x81\x91\xa1\x07#B\xb1\xc1\xd1\xf0$3Rr\x82\x92\xb2\xf1\x15CS\xc2\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf4\x9f\x91\x8a(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00\xff\xd9'
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
            time_module.sleep(0.1)
    
    while True:
        if not camera or not camera.isOpened():
            initialize_camera()
            time_module.sleep(1)
            continue
            
        success, frame = camera.read()
        if not success:
            break
        
        if monitoring_active and FACE_RECOGNITION_AVAILABLE:
            # Detect faces and check for unauthorized presence
            detected_students, face_locations = detect_faces_in_frame(frame)
            
            if detected_students:
                check_unauthorized_presence(detected_students)
                
                # Draw rectangles around detected faces
                for (top, right, bottom, left) in face_locations:
                    # Scale back up face locations
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/students')
def students():
    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        
        # Create new student
        student = Student(
            student_id=data['student_id'],
            name=data['name'],
            email=data['email']
        )
        
        # Process photo if provided
        if 'photo' in data:
            photo_data = data['photo'].split(',')[1]  # Remove data:image/jpeg;base64,
            photo_bytes = base64.b64decode(photo_data)
            
            # Save photo
            filename = secure_filename(f"{data['student_id']}.jpg")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(photo_path, 'wb') as f:
                f.write(photo_bytes)
            
            student.photo_path = photo_path
            
            # Generate face encoding
            if FACE_RECOGNITION_AVAILABLE:
                image = face_recognition.load_image_file(photo_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if face_encodings:
                    student.face_encoding = json.dumps(face_encodings[0].tolist())
                else:
                    print(f"Warning: No face detected in photo for {data['name']}")
            else:
                print("Face recognition not available - photo stored without encoding")
        
        db.session.add(student)
        db.session.commit()
        
        # Reload known faces
        load_known_faces()
        
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
        
        attendance = Attendance(
            student_id=data['student_id'],
            date=today,
            time_slot_id=data['time_slot_id'],
            status=data['status'],
            detected_at=datetime.now() if data['status'] == 'present' else None
        )
        
        # Check if attendance already exists
        existing = Attendance.query.filter_by(
            student_id=data['student_id'],
            date=today,
            time_slot_id=data['time_slot_id']
        ).first()
        
        if existing:
            existing.status = data['status']
            existing.detected_at = datetime.now() if data['status'] == 'present' else None
        else:
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
    return jsonify({'success': True, 'message': 'Monitoring started'})

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

# Automatic attendance marking at the start of each period
def auto_mark_attendance():
    current_time_slot = get_current_time_slot()
    if current_time_slot and current_time_slot.is_monitoring_period:
        today = datetime.now().date()
        students = Student.query.all()
        
        for student in students:
            # Check if attendance already marked
            existing = Attendance.query.filter_by(
                student_id=student.student_id,
                date=today,
                time_slot_id=current_time_slot.id
            ).first()
            
            if not existing:
                # Mark as absent by default
                attendance = Attendance(
                    student_id=student.student_id,
                    date=today,
                    time_slot_id=current_time_slot.id,
                    status='absent'
                )
                db.session.add(attendance)
        
        db.session.commit()

# Schedule automatic attendance marking
def schedule_tasks():
    time_slots = TimeSlot.query.filter_by(is_monitoring_period=True).all()
    for slot in time_slots:
        schedule.every().day.at(slot.start_time.strftime('%H:%M')).do(auto_mark_attendance)

def run_scheduler():
    while True:
        schedule.run_pending()
        time_module.sleep(60)

# Additional API endpoints for the frontend
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

@app.route('/acknowledge_alert', methods=['POST'])
def acknowledge_alert():
    try:
        data = request.get_json()
        alert = Alert.query.get(data['alert_id'])
        
        if alert:
            alert.status = 'acknowledged'
            db.session.commit()
            return jsonify({'success': True, 'message': 'Alert acknowledged'})
        else:
            return jsonify({'success': False, 'message': 'Alert not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_student', methods=['POST'])
def delete_student():
    try:
        data = request.get_json()
        student = Student.query.filter_by(student_id=data['student_id']).first()
        
        if student:
            db.session.delete(student)
            db.session.commit()
            load_known_faces()  # Reload face data
            return jsonify({'success': True, 'message': 'Student deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Student not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_time_slot', methods=['POST'])
def delete_time_slot():
    try:
        data = request.get_json()
        time_slot = TimeSlot.query.get(data['slot_id'])
        
        if time_slot:
            db.session.delete(time_slot)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Time slot deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Time slot not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/revoke_permission', methods=['POST'])
def revoke_permission():
    try:
        data = request.get_json()
        permission = SpecialPermission.query.get(data['permission_id'])
        
        if permission:
            db.session.delete(permission)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Permission revoked successfully'})
        else:
            return jsonify({'success': False, 'message': 'Permission not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_official', methods=['POST'])
def delete_official():
    try:
        data = request.get_json()
        official = Official.query.get(data['official_id'])
        
        if official:
            db.session.delete(official)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Official deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Official not found'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/bulk_attendance', methods=['POST'])
def bulk_attendance():
    try:
        data = request.get_json()
        action = data['action']
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        students = Student.query.all()
        time_slots = TimeSlot.query.filter_by(is_monitoring_period=True).all()
        
        for student in students:
            for time_slot in time_slots:
                # Check if attendance already exists
                existing = Attendance.query.filter_by(
                    student_id=student.student_id,
                    date=date,
                    time_slot_id=time_slot.id
                ).first()
                
                status = 'present' if action == 'mark_all_present' else 'absent'
                
                if existing:
                    existing.status = status
                    existing.detected_at = datetime.now() if status == 'present' else None
                else:
                    attendance = Attendance(
                        student_id=student.student_id,
                        date=date,
                        time_slot_id=time_slot.id,
                        status=status,
                        detected_at=datetime.now() if status == 'present' else None
                    )
                    db.session.add(attendance)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Bulk attendance updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_notification', methods=['POST'])
def test_notification():
    try:
        data = request.get_json()
        official = Official.query.get(data['official_id'])
        
        if official:
            # For demo, just print the notification
            print(f"TEST NOTIFICATION: Sent to {official.name} ({official.email}): EDUGUARD System Test")
            return jsonify({'success': True, 'message': 'Test notification sent'})
        else:
            return jsonify({'success': False, 'message': 'Official not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/save_notification_settings', methods=['POST'])
def save_notification_settings():
    try:
        data = request.get_json()
        # In a real implementation, you would save these settings to database
        # For demo, just return success
        print(f"Notification settings saved: {data}")
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_bulk_notification', methods=['POST'])
def test_bulk_notification():
    try:
        data = request.get_json()
        officials = Official.query.all()
        
        for official in officials:
            # For demo, just print the notification
            print(f"BULK TEST NOTIFICATION: Sent to {official.name} ({official.email}): {data['message']}")
        
        return jsonify({'success': True, 'message': f'Test notifications sent to {len(officials)} officials'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_known_faces()
        initialize_camera()
        
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Schedule tasks
        schedule_tasks()
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)