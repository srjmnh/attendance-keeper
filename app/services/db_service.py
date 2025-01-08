from flask import current_app, g
from datetime import datetime
from app.models.user import User
import firebase_admin
from firebase_admin import credentials, firestore
import os
import base64
import json

class DatabaseService:
    """Service class for database operations"""
    
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            # Initialize Firebase only once
            if not firebase_admin._apps:
                cred_json = base64.b64decode(os.getenv('FIREBASE_ADMIN_CREDENTIALS_BASE64')).decode('utf-8')
                cred = credentials.Certificate(json.loads(cred_json))
                firebase_admin.initialize_app(cred)
            cls._db = firestore.client()
        return cls._instance
    
    def __init__(self):
        """Initialize database service"""
        pass
    
    @property
    def db(self):
        """Get the Firestore client"""
        return self._db
    
    def get_db(self):
        """Get the Firestore client"""
        return self._db
    
    @classmethod
    def get_instance(cls):
        """Get or create database service instance"""
        if not hasattr(g, 'db_service'):
            g.db_service = cls()
        return g.db_service
    
    def get_user_by_id(self, user_id):
        """Get user by ID and return User model instance"""
        try:
            doc = self.db.collection('users').document(user_id).get()
            if doc.exists:
                user_data = doc.to_dict()
                return User(
                    id=doc.id,
                    email=user_data.get('email'),
                    name=user_data.get('name'),
                    role=user_data.get('role'),
                    password=user_data.get('password_hash')
                )
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    def get_user_by_email(self, email):
        """Get user by email and return User model instance"""
        try:
            query = self.db.collection('users').where('email', '==', email).limit(1).stream()
            for doc in query:
                user_data = doc.to_dict()
                # Debug logging
                print(f"User data from DB: {user_data}")
                return User(
                    id=doc.id,
                    email=user_data.get('email'),
                    name=user_data.get('name'),
                    role=user_data.get('role'),
                    password=user_data.get('password_hash')
                )
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def get_users_by_role(self, role):
        """Get all users with specified role"""
        try:
            users = []
            query = self.db.collection('users').where('role', '==', role).stream()
            for doc in query:
                user_data = doc.to_dict()
                users.append({
                    'id': doc.id,
                    **user_data
                })
            return users
        except Exception as e:
            current_app.logger.error(f"Error getting users by role: {str(e)}")
            return []
    
    def create_user(self, user_data):
        """Create a new user"""
        try:
            # Add timestamps
            user_data['created_at'] = datetime.utcnow().isoformat()
            user_data['updated_at'] = user_data['created_at']
            
            # Create document
            doc_ref = self.db.collection('users').document()
            doc_ref.set(user_data)
            
            return {
                'id': doc_ref.id,
                **user_data
            }
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            raise 