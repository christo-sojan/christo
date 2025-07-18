# EDUGUARD - Intelligent Campus Monitoring & Attendance System

## Overview

EDUGUARD is an advanced campus monitoring and attendance system that uses facial recognition technology to automatically track student attendance and detect unauthorized presence. The system provides real-time alerts to officials when students marked as absent are detected on campus during class hours.

## Features

### 🔐 Core Security Features
- **Real-time Camera Monitoring**: Live video feed with facial recognition
- **Automated Attendance Tracking**: Automatic attendance marking at class start times
- **Unauthorized Presence Detection**: Alerts when absent students are detected on campus
- **Special Permissions Management**: Handle authorized absences and special cases
- **Instant Alert System**: Real-time notifications to officials

### 📊 Management Features
- **Student Database**: Manage student profiles with facial recognition training
- **Time Slot Configuration**: Set up class periods and monitoring intervals
- **Attendance Reports**: View daily, weekly, and monthly attendance records
- **Official Management**: Configure notification recipients
- **Alert History**: Track and acknowledge security alerts

### 🎨 User Interface
- **Modern Web Interface**: Responsive design with Bootstrap 5
- **Live Dashboard**: Real-time statistics and monitoring status
- **Mobile-Friendly**: Works on desktop, tablet, and mobile devices
- **Intuitive Navigation**: Easy-to-use interface for all user levels

## System Requirements

### Software Requirements
- Python 3.8 or higher
- OpenCV 4.x
- Web browser (Chrome, Firefox, Safari, Edge)

### Hardware Requirements
- Camera/Webcam for video monitoring
- Minimum 4GB RAM (8GB recommended)
- Multi-core processor (for face recognition processing)
- 2GB free disk space

### Operating System Support
- Windows 10/11
- macOS 10.14+
- Linux (Ubuntu 18.04+, CentOS 7+)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd eduguard
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
The database will be automatically created when you first run the application.

### 4. Run the Application
```bash
python app.py
```

### 5. Access the Web Interface
Open your web browser and navigate to:
```
http://localhost:5000
```

## Quick Start Guide

### 1. First Time Setup

1. **Start the Application**
   ```bash
   python app.py
   ```

2. **Access the Dashboard**
   - Open http://localhost:5000 in your browser
   - You'll see the main dashboard with live camera feed

3. **Add Time Slots**
   - Navigate to "Time Slots" in the sidebar
   - Click "Add Preset Slots" for common college schedules
   - Or manually add custom time slots

4. **Add Students**
   - Go to "Students" section
   - Click "Add New Student"
   - Fill in student details and upload a clear photo
   - The system will automatically train facial recognition

5. **Add Officials**
   - Visit "Officials" section
   - Add officials who should receive alerts
   - Configure notification preferences

### 2. Daily Operations

1. **Start Monitoring**
   - Click "Start Monitoring" button in the top-right corner
   - Camera will begin facial recognition and alert detection

2. **Mark Attendance**
   - Go to "Attendance" section
   - Manually mark attendance or let the system auto-mark
   - Review and edit attendance as needed

3. **Handle Alerts**
   - Check "Alerts" section for unauthorized presence
   - Acknowledge alerts after investigation
   - Review alert history

4. **Grant Special Permissions**
   - Use "Permissions" section for authorized absences
   - Set date, time period, and reason
   - System won't generate alerts for permitted absences

## System Configuration

### Camera Settings
The system automatically detects the default camera (index 0). To use a different camera:

```python
# In app.py, modify the initialize_camera function
camera = cv2.VideoCapture(1)  # Change index as needed
```

### Face Recognition Accuracy
For better accuracy:
- Use clear, well-lit photos during student registration
- Ensure photos show the full face
- Avoid sunglasses or face coverings in registration photos
- Retrain if recognition accuracy decreases

### Notification Settings
Configure email notifications by setting up SMTP settings in the code:

```python
# Add email configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'your-email@gmail.com'
EMAIL_PASS = 'your-app-password'
```

## API Endpoints

The system provides REST API endpoints for integration:

### Student Management
- `POST /add_student` - Add new student
- `POST /delete_student` - Remove student
- `GET /api/students` - Get all students

### Attendance
- `POST /mark_attendance` - Mark attendance
- `POST /bulk_attendance` - Bulk attendance operations
- `GET /api/attendance_stats` - Get attendance statistics

### Alerts
- `GET /api/recent_alerts` - Get recent alerts
- `POST /acknowledge_alert` - Acknowledge alert

### Time Slots
- `POST /add_time_slot` - Add time slot
- `POST /delete_time_slot` - Remove time slot
- `GET /api/time_slots` - Get all time slots

## Security Features

### Data Protection
- Student photos are stored locally
- Face encodings are encrypted
- No external data transmission without explicit configuration

### Access Control
- Web interface can be secured with authentication
- API endpoints can be protected with tokens
- Role-based access control available

### Privacy Compliance
- GDPR and privacy law compliant
- Option to delete all student data
- Audit trail for all operations

## Troubleshooting

### Common Issues

1. **Camera Not Working**
   ```
   Error: Could not open camera
   Solution: Check camera permissions and ensure no other app is using it
   ```

2. **Face Recognition Not Accurate**
   ```
   Issue: Students not being recognized
   Solution: Re-register with better quality photos, ensure good lighting
   ```

3. **Slow Performance**
   ```
   Issue: High CPU usage during monitoring
   Solution: Reduce frame rate, use smaller resolution, upgrade hardware
   ```

4. **Database Errors**
   ```
   Issue: SQLite database locked
   Solution: Restart application, check file permissions
   ```

### Debug Mode
Run with debug logging:
```bash
python app.py --debug
```

### Performance Optimization
- Adjust face recognition tolerance (0.6 default)
- Reduce camera resolution for faster processing
- Use GPU acceleration if available

## Development

### Project Structure
```
eduguard/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── students.html
│   ├── alerts.html
│   ├── attendance.html
│   ├── permissions.html
│   ├── time_slots.html
│   └── officials.html
├── static/              # Static files
│   └── student_photos/  # Student photo storage
└── instance/            # Database files
    └── eduguard.db
```

### Adding New Features
1. Create new database models in `app.py`
2. Add corresponding HTML templates
3. Implement API endpoints
4. Update navigation in `base.html`

### Testing
```bash
# Install test dependencies
pip install pytest

# Run tests
pytest tests/
```

## Deployment

### Production Deployment
1. Use a production WSGI server (Gunicorn, uWSGI)
2. Set up reverse proxy (Nginx, Apache)
3. Configure SSL certificates
4. Set up proper database (PostgreSQL, MySQL)
5. Configure environment variables

### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment Variables
```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost/eduguard
export SECRET_KEY=your-secret-key
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the documentation

## Changelog

### Version 1.0.0
- Initial release
- Core facial recognition functionality
- Web interface
- Alert system
- Attendance tracking

## Acknowledgments

- OpenCV for computer vision capabilities
- Face Recognition library for facial detection
- Flask for web framework
- Bootstrap for UI components

---

**⚠️ Important Notes:**
- This system is designed for educational/institutional use
- Ensure compliance with local privacy laws
- Regular backups of student data recommended
- Keep the system updated for security patches