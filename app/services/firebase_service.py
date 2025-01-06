import os
import json
import logging

logger = logging.getLogger(__name__)

# Default development credentials
DEFAULT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "facial-f5096",
    "private_key_id": "development-key-id",
    "private_key": """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAx7/2UFuSqhF6LwBMwrGnPHGUuMJ0g4f8kWq/GOzHuJQsF8bH
Yl5gXe8LQZlHPLhGHGSC8JR5GMDTrYRmRI8rpRfGT5Q8G5UZBSvX0jQB4YqKuRuE
ByGXEQELXxf1d3iXIuW3K4KqRXvCm6Lq4l2JvYQzD6QGCC6dEBqqQQEQEQEQEQEQ
EQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQ
EQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEQEw
DQYJKoZIhvcNAQELBQADggEBAMW0HVDLQcbIsY9ewTxGorwOVj4Dy/SkfxDq/6pn
-----END RSA PRIVATE KEY-----""",
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
            if not creds["private_key"].startswith("-----BEGIN"):
                # Try to format as RSA key
                key = creds["private_key"].replace("\\n", "\n")
                creds["private_key"] = f"-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----"
            return creds
        except Exception as e:
            logger.error(f"Error parsing Firebase credentials: {e}")
            logger.warning("Falling back to development credentials")
            return DEFAULT_CREDENTIALS
    
    # Use development credentials if no environment variable
    logger.warning("FIREBASE_ADMIN_CREDENTIALS not found, using development credentials")
    return DEFAULT_CREDENTIALS 