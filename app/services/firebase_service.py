import os
import json
import logging

logger = logging.getLogger(__name__)

# Default development credentials
DEFAULT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "facial-f5096",
    "private_key_id": "development-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEogIBAAKCAQEAwJENDz5pf2pNjbRyXcNaHpZFwikoHdmHxHPPcJKijI6KQYhQ\nXjR3F7IW7zZHk7GmWWiHBJTm9doQNj9M7TnmYDqrWIJh1zDqMb+7RoCI0Qz1r/m+\nEYhPVZkgqq6phVUCncIBHrSP6cjD4KouPzBxgHCQk8M2yKdzGKsf6fZkGD4rHPvM\nGLwBp6Zmpj0lBqGuXHDXeYwwZw1zXxqEhXC2z4MUGl8LrYqHVkXb+1Cf6TEVcXzO\nQA1vLuZ6mXz6h6PuABqx/qLF4OoQhu8zqudqGk0/s3IxvPFkQ/g0aHiXzk3UHn5o\nBQVmGxaZQJi6sBukaw1AF6JPp1p+tF1dXuGj2QIDAQABAoIBAA8Yk4z6c9wr6yiE\ns7BzD6H9kaHW0qxAy0fEi0H1ZI9U\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-dev@facial-f5096.iam.gserviceaccount.com",
    "client_id": "development-client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-dev%40facial-f5096.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

def get_firebase_credentials():
    """Get Firebase credentials from environment or use development credentials"""
    # Try to get from environment first
    json_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS")
    if json_cred_str:
        try:
            creds = json.loads(json_cred_str)
            # Ensure private key is properly formatted
            if not creds["private_key"].startswith("-----BEGIN PRIVATE KEY-----\n"):
                creds["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{creds['private_key']}\n-----END PRIVATE KEY-----\n"
            return creds
        except Exception as e:
            logger.error(f"Error parsing Firebase credentials: {e}")
            logger.warning("Falling back to development credentials")
            return DEFAULT_CREDENTIALS
    
    # Use development credentials if no environment variable
    logger.warning("FIREBASE_ADMIN_CREDENTIALS not found, using development credentials")
    return DEFAULT_CREDENTIALS 