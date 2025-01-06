import os
import json
import logging

logger = logging.getLogger(__name__)

# Default development credentials
DEFAULT_CREDENTIALS = {
    "type": "service_account",
    "project_id": "facial-f5096",
    "private_key_id": "dummy-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC9QFi8Lg/SgXFZ\nDHX8SW1UupenBQZt3j8j+n4dgKWaKxDJGFj7oM7YHvhQWk6E1cZOVHnMHF9wH5WR\nzD8kZTBl4qVXob8kPD/y5E4Zc5gTAGwuUwCsRUpXhqQjyZvUX4JeGTVxEXq0PhM+\nGxZHZCsNa5YwDcB5S3hmA9YrqOW3cHtytDGcvKmwGBpYHq9WlvuM3mQQJrB0Ow+p\nZdHHxj5w3h9FZX8kqw3YZBjcM1ZJqK3gYqZCxXqnkLcELytaE0LWFLDdQQHE+zRz\nfkWwHZFqRqD4LyBBaqYCjrUeVJbgQj4qL4vuBcnEfRtwxG+BqLI6iyDmyWDBZBr5\nAgMBAAECggEBAKwGH3kHj5CZchY9CFc5+NkQmTe3XWRgApTfuQJ5r0XqRWp8vMXk\nZz/BfX7U4ZJxQwWwiFUu9WXZLclosure+dummy+key+for+development+only\nAgMBAAECggEBAKwGH3kHj5CZchY9CFc5+NkQmTe3XWRgApTfuQJ5r0XqRWp8vMXk\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-xxxxx@facial-f5096.iam.gserviceaccount.com",
    "client_id": "dummy-client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40facial-f5096.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
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