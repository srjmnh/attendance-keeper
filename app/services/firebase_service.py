import os
import json
import logging

logger = logging.getLogger(__name__)

def get_firebase_credentials():
    """Get Firebase credentials from environment"""
    json_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS")
    if not json_cred_str:
        logger.error("FIREBASE_ADMIN_CREDENTIALS environment variable not found")
        raise ValueError("Firebase credentials not found in environment")
        
    try:
        return json.loads(json_cred_str)
    except Exception as e:
        logger.error(f"Error parsing Firebase credentials: {e}")
        raise ValueError("Invalid Firebase credentials format") 