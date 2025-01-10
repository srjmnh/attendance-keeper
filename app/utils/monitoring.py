"""Monitoring and health check utilities for the application."""
from flask import Blueprint, jsonify, current_app
from datetime import datetime
import psutil
import firebase_admin
import boto3
import redis
from functools import wraps
import time

monitoring_bp = Blueprint('monitoring', __name__)

class HealthCheck:
    """Health check utility class."""
    
    @staticmethod
    def check_firebase():
        """Check Firebase connection."""
        try:
            # Try to access Firestore
            db = firebase_admin.firestore.client()
            db.collection('health_check').limit(1).get()
            return True, "Firebase connection successful"
        except Exception as e:
            return False, f"Firebase connection failed: {str(e)}"
    
    @staticmethod
    def check_aws():
        """Check AWS services."""
        try:
            # Check Rekognition
            rekognition = boto3.client('rekognition')
            rekognition.list_collections()
            return True, "AWS connection successful"
        except Exception as e:
            return False, f"AWS connection failed: {str(e)}"
    
    @staticmethod
    def check_redis():
        """Check Redis connection if configured."""
        if current_app.config.get('CACHE_TYPE') == 'redis':
            try:
                redis_client = redis.from_url(current_app.config['CACHE_REDIS_URL'])
                redis_client.ping()
                return True, "Redis connection successful"
            except Exception as e:
                return False, f"Redis connection failed: {str(e)}"
        return True, "Redis not configured"
    
    @staticmethod
    def check_system_resources():
        """Check system resources."""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return True, {
                'cpu_usage': f"{cpu_percent}%",
                'memory_usage': f"{memory.percent}%",
                'disk_usage': f"{disk.percent}%"
            }
        except Exception as e:
            return False, f"System resource check failed: {str(e)}"

def monitor_performance(f):
    """Decorator to monitor endpoint performance."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Execute the function
        response = f(*args, **kwargs)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Log performance metrics
        current_app.logger.info(
            f"Performance: {f.__name__} took {execution_time:.2f} seconds"
        )
        
        return response
    return decorated_function

@monitoring_bp.route('/health')
def health_check():
    """Health check endpoint."""
    health = HealthCheck()
    
    # Perform all health checks
    firebase_status, firebase_message = health.check_firebase()
    aws_status, aws_message = health.check_aws()
    redis_status, redis_message = health.check_redis()
    system_status, system_metrics = health.check_system_resources()
    
    # Determine overall status
    overall_status = all([
        firebase_status,
        aws_status,
        redis_status,
        system_status
    ])
    
    response = {
        'status': 'healthy' if overall_status else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'firebase': {
                'status': 'up' if firebase_status else 'down',
                'message': firebase_message
            },
            'aws': {
                'status': 'up' if aws_status else 'down',
                'message': aws_message
            },
            'redis': {
                'status': 'up' if redis_status else 'down',
                'message': redis_message
            }
        },
        'system': system_metrics if system_status else {'error': system_metrics}
    }
    
    status_code = 200 if overall_status else 503
    return jsonify(response), status_code

@monitoring_bp.route('/metrics')
def metrics():
    """Metrics endpoint."""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics (example)
        metrics_data = {
            'system': {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'memory_available': memory.available,
                'disk_free': disk.free
            },
            'application': {
                'uptime': time.time() - psutil.boot_time(),
                'process_memory': psutil.Process().memory_info().rss,
                'open_files': len(psutil.Process().open_files()),
                'threads': psutil.Process().num_threads()
            }
        }
        
        return jsonify(metrics_data)
    except Exception as e:
        current_app.logger.error(f"Error collecting metrics: {str(e)}")
        return jsonify({'error': 'Failed to collect metrics'}), 500 