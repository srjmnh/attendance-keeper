# AttendanceAI

A modern attendance management system with face recognition capabilities, built with Flask and modern web technologies.

## Technical Architecture

### Core Components

1. **Application Factory (`app/__init__.py`)**
   - Creates and configures Flask application
   - Initializes extensions (Flask-Login, CSRF protection)
   - Registers blueprints
   - Sets up error handlers and logging
   - Configures Firebase and AWS services

2. **Blueprints Organization**
   - `auth_bp`: Authentication and user management
   - `main_bp`: Dashboard and main views
   - `admin_bp`: Administrative functions
   - `teacher_bp`: Teacher-specific functionality
   - `recognition_bp`: Face recognition features
   - `attendance_bp`: Attendance tracking
   - `chat_bp`: AI assistant integration
   - `ai_bp`: AI-related functionalities

### Frontend Structure

1. **Base Template (`app/templates/base.html`)**
   - Core layout and navigation
   - Mobile-first responsive design
   - Key components:
     ```
     ├── Mobile Header (mobile-only)
     ├── Sidebar Navigation
     │   ├── Logo
     │   ├── Role-based Navigation
     │   └── User Menu
     ├── Main Content Area
     ├── Toast Notifications
     └── Chatbot Interface
     ```

2. **Mobile Optimizations**
   ```css
   /* Key Mobile Features */
   - Responsive drawer navigation
   - Frosted glass effects
   - Touch-optimized navigation
   - Adaptive layouts
   - Mobile-specific styling
   ```

3. **Role-Based Views**
   - Admin Interface:
     - Teacher management
     - Student management
     - Subject management
   - Teacher Interface:
     - Student viewing
     - Attendance tracking
     - Face registration
   - Student Interface:
     - Attendance viewing
     - Face recognition

### Technical Details

1. **Mobile-First Design**
   ```css
   @media (max-width: 1024px) {
     /* Mobile Navigation */
     #sidebar {
       position: fixed;
       width: 280px;
       transform: translateX(-100%);
     }
     
     /* Mobile Header */
     .mobile-header {
       backdrop-filter: blur(12px);
       background-color: rgba(255, 255, 255, 0.8);
     }
     
     /* Touch Optimizations */
     .mobile-nav-item {
       padding: 0.75rem 1rem;
       border-radius: 0.5rem;
     }
   }
   ```

2. **Blueprint Structure**
   ```python
   # Blueprint Registration
   app.register_blueprint(auth_bp)
   app.register_blueprint(main_bp)
   app.register_blueprint(admin_bp)
   app.register_blueprint(teacher_bp)
   app.register_blueprint(recognition_bp)
   app.register_blueprint(attendance_bp)
   app.register_blueprint(chat_bp)
   ```

3. **File Organization**
   ```
   app/
   ├── __init__.py           # Application factory
   ├── routes/
   │   ├── __init__.py       # Blueprint registration
   │   ├── admin.py          # Admin routes
   │   ├── auth.py           # Authentication
   │   ├── teacher.py        # Teacher functionality
   │   └── main.py           # Core routes
   ├── templates/
   │   ├── base.html         # Base template
   │   ├── admin/            # Admin templates
   │   ├── teacher/          # Teacher templates
   │   └── recognition/      # Face recognition
   └── static/
       ├── css/              # Stylesheets
       └── js/               # JavaScript files
   ```

4. **Key Features**
   - Role-based access control
   - Real-time face recognition
   - Mobile-optimized UI
   - AI-powered assistance
   - Responsive layouts
   - Touch-friendly interface

### Development Guidelines

1. **Adding New Features**
   ```bash
   # 1. Create blueprint
   mkdir app/routes/feature_name
   touch app/routes/feature_name/{__init__,routes}.py

   # 2. Register blueprint
   # In app/__init__.py:
   from app.routes import feature_name_bp
   app.register_blueprint(feature_name_bp)
   ```

2. **Mobile Development**
   - Use mobile-first approach
   - Test on various screen sizes
   - Follow touch target guidelines
   - Implement responsive images
   - Optimize performance

3. **Template Structure**
   ```html
   {% extends "base.html" %}
   {% block content %}
     <!-- Page-specific content -->
   {% endblock %}
   ```

4. **CSS Organization**
   - Use utility classes (Tailwind)
   - Follow mobile-first pattern
   - Implement dark mode support
   - Maintain consistent spacing

### Security Considerations

1. **Authentication**
   - Flask-Login integration
   - Role-based access control
   - Secure session management

2. **Data Protection**
   - CSRF protection
   - Secure headers
   - Input validation

3. **API Security**
   - Rate limiting
   - Request validation
   - Error handling

### Deployment

1. **Requirements**
   - Python 3.8+
   - Firebase Admin SDK
   - AWS Rekognition
   - Redis (optional, for caching)

2. **Environment Variables**
   ```bash
   FLASK_APP=run.py
   FLASK_ENV=production
   SECRET_KEY=your-secret-key
   FIREBASE_ADMIN_CREDENTIALS_BASE64=base64-encoded-credentials
   AWS_ACCESS_KEY_ID=your-aws-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret
   ```

3. **Production Setup**
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Run with gunicorn
   gunicorn run:app
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Follow coding standards
4. Submit pull request

### License

MIT License - See LICENSE file for details

