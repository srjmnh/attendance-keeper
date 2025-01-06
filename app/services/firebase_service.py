import os
import json
import logging

logger = logging.getLogger(__name__)

# Default development credentials
DEFAULT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "facial-f5096",
    "private_key_id": "your-private-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDFtB1Qy0HGyLGP\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-xxxxx@facial-f5096.iam.gserviceaccount.com",
    "client_id": "xxxxxxxxxxxxxxxxxxxxx",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40facial-f5096.iam.gserviceaccount.com"
}

def get_firebase_credentials():
    """Get Firebase credentials from environment or use development credentials"""
    # Try to get from environment first
    json_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS")
    if json_cred_str:
        try:
            return json.loads(json_cred_str)
        except Exception as e:
            logger.error(f"Error parsing Firebase credentials: {e}")
            logger.warning("Falling back to development credentials")
            return DEFAULT_CREDENTIALS
    
    # Use development credentials if no environment variable
    logger.warning("FIREBASE_ADMIN_CREDENTIALS not found, using development credentials")
    return DEFAULT_CREDENTIALS 