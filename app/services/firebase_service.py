import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import tempfile
import os
from flask import current_app
from datetime import datetime

def initialize_firebase(credentials_base64):
    """Initialize Firebase Admin SDK with credentials
    
    Args:
        credentials_base64: Base64 encoded Firebase service account credentials
    """
    try:
        # Decode base64 credentials
        credentials_json = base64.b64decode(credentials_base64)
        credentials_dict = json.loads(credentials_json)
        
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(credentials_dict)
        firebase_admin.initialize_app(cred)
        
        # Initialize and return Firestore client
        return firestore.client()
    except Exception as e:
        current_app.logger.error(f"Firebase initialization error: {str(e)}")
        raise ValueError(f"Failed to initialize Firebase: {str(e)}")

def get_user_by_email(email):
    """Get user data from Firebase by email"""
    try:
        users_ref = current_app.db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).stream()
        
        for doc in query:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            return user_data
        
        return None
    except Exception as e:
        current_app.logger.error(f"Error getting user by email: {str(e)}")
        raise

def get_user_by_id(user_id):
    """Get user data from Firebase by ID"""
    try:
        doc = current_app.db.collection('users').document(user_id).get()
        
        if doc.exists:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            return user_data
        
        return None
    except Exception as e:
        current_app.logger.error(f"Error getting user by ID: {str(e)}")
        raise

def create_user(user_data):
    """Create a new user in Firebase"""
    try:
        # Add created_at timestamp
        user_data['created_at'] = datetime.utcnow().isoformat()
        
        # Create user document
        doc_ref = current_app.db.collection('users').document()
        doc_ref.set(user_data)
        
        # Return user data with ID
        user_data['id'] = doc_ref.id
        return user_data
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        raise

def update_user(user_id, update_data):
    """Update user data in Firebase"""
    try:
        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user document
        doc_ref = current_app.db.collection('users').document(user_id)
        doc_ref.update(update_data)
        
        # Return updated user data
        updated_doc = doc_ref.get()
        if updated_doc.exists:
            user_data = updated_doc.to_dict()
            user_data['id'] = updated_doc.id
            return user_data
        
        return None
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        raise

def delete_user(user_id):
    """Delete user from Firebase"""
    try:
        current_app.db.collection('users').document(user_id).delete()
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        raise

def get_user_subjects(user_id):
    """Get subjects associated with a user"""
    try:
        # All users can see all subjects
        subjects = current_app.db.collection('subjects').stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in subjects]
    except Exception as e:
        current_app.logger.error(f"Error getting user subjects: {str(e)}")
        raise 