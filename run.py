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
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('DEBUG', 'false').lower() == 'true'
    ) 