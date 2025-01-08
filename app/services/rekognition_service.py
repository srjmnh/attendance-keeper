import os
import boto3
import base64
from io import BytesIO
from PIL import Image, ImageEnhance
from flask import current_app

class RekognitionService:
    """Service for AWS Rekognition operations"""
    
    def __init__(self):
        """Initialize Rekognition client"""
        self.client = boto3.client(
            'rekognition',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.collection_id = os.getenv('AWS_COLLECTION_ID', 'attendance-faces')
    
    def decode_base64_image(self, base64_string):
        """Decode base64 image and enhance it"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_string)
            
            # Open and enhance image
            image = Image.open(BytesIO(image_bytes))
            
            # Enhance image
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
            
            # Convert back to bytes
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            return buffer.getvalue()
            
        except Exception as e:
            current_app.logger.error(f"Error decoding image: {str(e)}")
            raise
    
    def index_face(self, image_bytes, external_image_id):
        """Index a face in the Rekognition collection"""
        try:
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=external_image_id,
                MaxFaces=1,
                QualityFilter="AUTO",
                DetectionAttributes=['ALL']
            )
            
            if not response['FaceRecords']:
                raise ValueError("No face detected in the image")
            
            return response['FaceRecords'][0]
            
        except Exception as e:
            current_app.logger.error(f"Error indexing face: {str(e)}")
            raise
    
    def detect_faces(self, image_bytes):
        """Detect faces in an image"""
        try:
            response = self.client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            return response['FaceDetails']
            
        except Exception as e:
            current_app.logger.error(f"Error detecting faces: {str(e)}")
            raise
    
    def search_faces(self, image_bytes):
        """Search for faces in the collection"""
        try:
            response = self.client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=1,
                FaceMatchThreshold=90
            )
            return response['FaceMatches']
            
        except Exception as e:
            current_app.logger.error(f"Error searching faces: {str(e)}")
            raise 