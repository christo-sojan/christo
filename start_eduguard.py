#!/usr/bin/env python3
"""
EDUGUARD Startup Script
This script helps users get started with the EDUGUARD system by checking dependencies
and providing setup guidance.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = {
        'flask': 'flask',
        'opencv-python': 'cv2', 
        'face-recognition': 'face_recognition',
        'numpy': 'numpy',
        'pillow': 'PIL',
        'flask-sqlalchemy': 'flask_sqlalchemy',
        'flask-cors': 'flask_cors'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name}")
            missing_packages.append(package_name)
    
    return missing_packages

def install_dependencies(missing_packages):
    """Install missing dependencies."""
    if not missing_packages:
        return True
    
    print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install'
        ] + missing_packages)
        print("✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies.")
        print("   Please run: pip install -r requirements.txt")
        return False

def check_camera():
    """Check if camera is available."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("✅ Camera detected and available")
            cap.release()
            return True
        else:
            print("⚠️  Camera not detected or in use by another application")
            print("   The system will work without camera (manual mode)")
            return False
    except ImportError:
        print("⚠️  OpenCV not available - camera functionality disabled")
        print("   The system will work in manual mode only")
        return False
    except Exception as e:
        print(f"⚠️  Camera check failed: {e}")
        print("   The system will work in manual mode only")
        return False

def create_directories():
    """Create necessary directories."""
    directories = [
        'static',
        'static/student_photos',
        'templates',
        'instance'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory created/verified: {directory}")

def print_welcome():
    """Print welcome message and setup instructions."""
    print("=" * 60)
    print("🛡️  EDUGUARD - Intelligent Campus Monitoring System")
    print("=" * 60)
    print()

def print_setup_guide():
    """Print quick setup guide."""
    print("\n🚀 QUICK SETUP GUIDE:")
    print("1. Start the application: python app.py")
    print("2. Open browser: http://localhost:5000")
    print("3. Add time slots (Time Slots → Add Preset Slots)")
    print("4. Add students (Students → Add New Student)")
    print("5. Add officials (Officials → Add Official)")
    print("6. Start monitoring (Start Monitoring button)")
    print()

def print_troubleshooting():
    """Print troubleshooting tips."""
    print("🔧 TROUBLESHOOTING:")
    print("• Camera issues: Ensure no other app is using the camera")
    print("• Face recognition: Use clear, well-lit photos")
    print("• Performance: Close other applications to free up resources")
    print("• Support: Check README.md for detailed documentation")
    print()

def main():
    """Main startup function."""
    print_welcome()
    
    print("🔍 SYSTEM CHECK:")
    print("-" * 20)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    print("\n📋 DEPENDENCY CHECK:")
    print("-" * 20)
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} required packages.")
        install_choice = input("Install missing packages now? (y/n): ").lower().strip()
        
        if install_choice in ['y', 'yes']:
            if not install_dependencies(missing):
                print("\n❌ Setup failed. Please install dependencies manually.")
                sys.exit(1)
        else:
            print("\n⚠️  Some features may not work without all dependencies.")
    
    # Check camera
    print("\n📷 CAMERA CHECK:")
    print("-" * 15)
    check_camera()
    
    # Create directories
    print("\n📁 DIRECTORY SETUP:")
    print("-" * 18)
    create_directories()
    
    # Check if main app exists
    if not os.path.exists('app.py'):
        print("\n❌ app.py not found in current directory.")
        print("   Please ensure you're in the correct project folder.")
        sys.exit(1)
    
    print("\n✅ System check complete!")
    
    # Show setup guide
    print_setup_guide()
    print_troubleshooting()
    
    # Ask if user wants to start the application
    start_choice = input("Start EDUGUARD now? (y/n): ").lower().strip()
    
    if start_choice in ['y', 'yes']:
        print("\n🚀 Starting EDUGUARD...")
        print("   Press Ctrl+C to stop the application")
        print("   Open http://localhost:5000 in your browser")
        print("-" * 60)
        
        try:
            # Import and run the main application
            import app
        except KeyboardInterrupt:
            print("\n\n👋 EDUGUARD stopped. Thank you for using our system!")
        except Exception as e:
            print(f"\n❌ Error starting application: {e}")
            print("   Check the troubleshooting section in README.md")
    else:
        print("\n👋 Setup complete! Run 'python app.py' when ready to start.")

if __name__ == "__main__":
    main()