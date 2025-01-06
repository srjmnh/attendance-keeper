import os
from app import create_app

# Get environment
env = os.getenv('FLASK_ENV', 'development')

# Create app instance
app = create_app()

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    # Run the application
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=int(app.config.get('PORT', 5000)),
        debug=app.config.get('DEBUG', False)
    ) 