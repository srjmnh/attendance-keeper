import boto3
from PIL import Image, ImageEnhance
import io
import base64
from flask import current_app
import cv2
import numpy as np

class RekognitionService:
    def __init__(self):
        self.client = boto3.client(
            'rekognition',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION']
        )
        self.collection_id = current_app.config['COLLECTION_ID']
    
    def create_collection(self):
        """Create collection if it doesn't exist"""
        try:
            self.client.create_collection(CollectionId=self.collection_id)
            return True
        except self.client.exceptions.ResourceAlreadyExistsException:
            return True
        except Exception as e:
            raise Exception(f"Failed to create collection: {str(e)}")
    
    def enhance_image(self, image_bytes):
        """Enhance image quality for better face detection"""
        # Convert bytes to PIL Image
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Convert PIL image to OpenCV format
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Increase brightness and contrast
        alpha = 1.2  # Contrast control (1.0-3.0)
        beta = 30    # Brightness control (0-100)
        enhanced_cv_image = cv2.convertScaleAbs(cv_image, alpha=alpha, beta=beta)
        
        # Convert back to PIL Image
        enhanced_pil_image = Image.fromarray(cv2.cvtColor(enhanced_cv_image, cv2.COLOR_BGR2RGB))
        
        # Convert to bytes
        buffered = io.BytesIO()
        enhanced_pil_image.save(buffered, format="JPEG")
        return buffered.getvalue()
    
    def index_face(self, image_bytes, external_image_id):
        """Index a face in the collection"""
        try:
            # Enhance image
            enhanced_image = self.enhance_image(image_bytes)
            
            # Index face
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': enhanced_image},
                ExternalImageId=external_image_id,
                DetectionAttributes=['ALL'],
                QualityFilter='AUTO'
            )
            
            if not response.get('FaceRecords'):
                raise Exception("No face detected in the image")
            
            return response['FaceRecords'][0]
        except Exception as e:
            raise Exception(f"Failed to index face: {str(e)}")
    
    def search_faces(self, image_bytes, max_faces=1, threshold=60):
        """Search for faces in the collection"""
        try:
            # Enhance image
            enhanced_image = self.enhance_image(image_bytes)
            
            # Search faces
            response = self.client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': enhanced_image},
                MaxFaces=max_faces,
                FaceMatchThreshold=threshold
            )
            
            return response.get('FaceMatches', [])
        except Exception as e:
            raise Exception(f"Failed to search faces: {str(e)}")
    
    def detect_faces(self, image_bytes):
        """Detect faces in an image"""
        try:
            # Enhance image
            enhanced_image = self.enhance_image(image_bytes)
            
            # Detect faces
            response = self.client.detect_faces(
                Image={'Bytes': enhanced_image},
                Attributes=['ALL']
            )
            
            return response.get('FaceDetails', [])
        except Exception as e:
            raise Exception(f"Failed to detect faces: {str(e)}")
    
    @staticmethod
    def decode_base64_image(base64_string):
        """Decode base64 image to bytes"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            return base64.b64decode(base64_string)
        except Exception as e:
            raise Exception(f"Failed to decode base64 image: {str(e)}") 