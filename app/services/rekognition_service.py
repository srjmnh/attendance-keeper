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
        self.collection_id = os.getenv('AWS_COLLECTION_ID', 'students')
    
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
    
    def crop_face(self, image_bytes, bounding_box):
        """Crop face from image using bounding box"""
        try:
            image = Image.open(BytesIO(image_bytes))
            width, height = image.size
            
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)
            
            # Add some padding around the face
            padding = int(min(width, height) * 0.1)  # 10% padding
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(width, right + padding)
            bottom = min(height, bottom + padding)
            
            face_image = image.crop((left, top, right, bottom))
            
            # Convert to bytes
            buffer = BytesIO()
            face_image.save(buffer, format="JPEG")
            return buffer.getvalue()
            
        except Exception as e:
            current_app.logger.error(f"Error cropping face: {str(e)}")
            raise
    
    def search_faces(self, image_bytes, face_index=0):
        """Search for faces in the collection"""
        try:
            # First detect faces to get bounding boxes
            faces = self.detect_faces(image_bytes)
            
            if not faces or face_index >= len(faces):
                current_app.logger.info(f"No faces found or face_index {face_index} out of range")
                return []
                
            # Get the face we want to search for
            face = faces[face_index]
            
            try:
                # Crop the face using its bounding box
                face_bytes = self.crop_face(image_bytes, face['BoundingBox'])
                
                # Search for the cropped face using search_faces_by_image
                try:
                    response = self.client.search_faces_by_image(
                        CollectionId=self.collection_id,
                        Image={'Bytes': face_bytes},
                        MaxFaces=1,
                        FaceMatchThreshold=80
                    )
                    current_app.logger.info(f"Search response for face {face_index}: {response}")
                    return response.get('FaceMatches', [])
                    
                except self.client.exceptions.InvalidParameterException as e:
                    current_app.logger.error(f"Invalid parameters for face search: {str(e)}")
                    return []
                except self.client.exceptions.ResourceNotFoundException as e:
                    current_app.logger.error(f"Collection not found: {str(e)}")
                    return []
                except self.client.exceptions.InvalidImageFormatException as e:
                    current_app.logger.error(f"Invalid image format: {str(e)}")
                    return []
                except self.client.exceptions.ImageTooLargeException as e:
                    current_app.logger.error(f"Image too large: {str(e)}")
                    return []
                except self.client.exceptions.AccessDeniedException as e:
                    current_app.logger.error(f"Access denied to Rekognition: {str(e)}")
                    raise
                except self.client.exceptions.ProvisionedThroughputExceededException as e:
                    current_app.logger.error(f"Throughput exceeded: {str(e)}")
                    return []
                except self.client.exceptions.ThrottlingException as e:
                    current_app.logger.error(f"Request throttled: {str(e)}")
                    return []
                except Exception as e:
                    current_app.logger.error(f"Error searching for face: {str(e)}")
                    return []
                
            except Exception as e:
                current_app.logger.error(f"Error processing cropped face: {str(e)}")
                return []
            
        except Exception as e:
            current_app.logger.error(f"Error in face detection: {str(e)}")
            raise 