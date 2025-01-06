import os
from app import create_app

app = create_app(os.getenv('FLASK_CONFIG', 'production'))

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 