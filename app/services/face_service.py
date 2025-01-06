"""Face recognition service using AWS Rekognition"""

import io
import logging
from typing import Dict, List, Optional, Tuple

import boto3
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from botocore.exceptions import ClientError
from flask import current_app

class FaceService:
    """Service for handling facial recognition operations"""

    def __init__(self):
        """Initialize the face recognition service"""
        self.client = boto3.client(
            'rekognition',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION']
        )
        self.collection_id = current_app.config['AWS_COLLECTION_ID']
        self.logger = logging.getLogger(__name__)

        # Ensure collection exists
        self._create_collection_if_not_exists()

    def _create_collection_if_not_exists(self) -> None:
        """Create AWS Rekognition collection if it doesn't exist"""
        try:
            self.client.describe_collection(CollectionId=self.collection_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.client.create_collection(CollectionId=self.collection_id)
                self.logger.info(f"Created collection: {self.collection_id}")
            else:
                raise

    def enhance_image(self, image_bytes: bytes) -> bytes:
        """Enhance image quality for better recognition"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if larger than maximum size
            max_size = current_app.config['IMAGE_MAX_SIZE']
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Enhance image
            enhancers = {
                'brightness': current_app.config['IMAGE_BRIGHTNESS'],
                'contrast': current_app.config['IMAGE_CONTRAST'],
                'sharpness': current_app.config['IMAGE_SHARPNESS']
            }

            for enhancer_type, factor in enhancers.items():
                if factor != 1.0:
                    enhancer = getattr(ImageEnhance, enhancer_type.capitalize())(image)
                    image = enhancer.enhance(factor)

            # Convert back to bytes
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=current_app.config['IMAGE_QUALITY'])
            return buffer.getvalue()

        except Exception as e:
            self.logger.error(f"Error enhancing image: {str(e)}")
            return image_bytes

    def register_face(self, image_bytes: bytes, external_id: str) -> Dict:
        """Register a face in the AWS collection"""
        try:
            # Enhance image quality
            enhanced_image = self.enhance_image(image_bytes)

            # Detect faces first to validate quality
            faces = self.detect_faces(enhanced_image)
            if not faces:
                return {'error': 'No face detected in the image'}
            if len(faces) > 1:
                return {'error': 'Multiple faces detected in the image'}

            face = faces[0]
            if face['quality'] < current_app.config['FACE_MIN_QUALITY']:
                return {'error': 'Image quality too low'}
            if face['confidence'] < current_app.config['FACE_MIN_CONFIDENCE']:
                return {'error': 'Face detection confidence too low'}

            # Index face
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': enhanced_image},
                ExternalImageId=external_id,
                MaxFaces=1,
                QualityFilter=current_app.config['AWS_QUALITY_FILTER'],
                DetectionAttributes=['ALL']
            )

            if not response['FaceRecords']:
                return {'error': 'Failed to index face'}

            face_record = response['FaceRecords'][0]
            return {
                'face_id': face_record['Face']['FaceId'],
                'confidence': face_record['Face']['Confidence'],
                'quality': face['quality']
            }

        except ClientError as e:
            self.logger.error(f"AWS error registering face: {str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Error registering face: {str(e)}")
            return {'error': str(e)}

    def detect_faces(self, image_bytes: bytes) -> List[Dict]:
        """Detect faces in an image and return their attributes"""
        try:
            response = self.client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )

            faces = []
            for face in response['FaceDetails']:
                # Calculate face size relative to image
                bbox = face['BoundingBox']
                face_size = min(bbox['Width'], bbox['Height']) * 100

                # Skip if face is too small
                if face_size < current_app.config['FACE_MIN_SIZE']:
                    continue

                faces.append({
                    'confidence': face['Confidence'],
                    'quality': face['Quality']['Brightness'] * face['Quality']['Sharpness'],
                    'pose': face['Pose'],
                    'emotions': face['Emotions'],
                    'landmarks': face['Landmarks'],
                    'bounding_box': bbox
                })

            return faces

        except ClientError as e:
            self.logger.error(f"AWS error detecting faces: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error detecting faces: {str(e)}")
            return []

    def search_faces(self, image_bytes: bytes) -> List[Dict]:
        """Search for matching faces in the collection"""
        try:
            # Enhance image quality
            enhanced_image = self.enhance_image(image_bytes)

            # Detect faces first
            faces = self.detect_faces(enhanced_image)
            if not faces:
                return []

            matches = []
            for face in faces:
                if face['confidence'] < current_app.config['FACE_MIN_CONFIDENCE']:
                    continue

                # Search for face in collection
                response = self.client.search_faces_by_image(
                    CollectionId=self.collection_id,
                    Image={'Bytes': enhanced_image},
                    MaxFaces=current_app.config['AWS_MAX_FACES'],
                    FaceMatchThreshold=current_app.config['AWS_FACE_MATCH_THRESHOLD']
                )

                for match in response['FaceMatches']:
                    matches.append({
                        'face_id': match['Face']['FaceId'],
                        'external_id': match['Face']['ExternalImageId'],
                        'confidence': match['Similarity'],
                        'bounding_box': face['bounding_box']
                    })

            return matches

        except ClientError as e:
            self.logger.error(f"AWS error searching faces: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error searching faces: {str(e)}")
            return []

    def delete_face(self, face_id: str) -> bool:
        """Delete a face from the collection"""
        try:
            response = self.client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            return bool(response['DeletedFaces'])

        except ClientError as e:
            self.logger.error(f"AWS error deleting face: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting face: {str(e)}")
            return False

    def delete_faces_by_external_id(self, external_id: str) -> bool:
        """Delete all faces associated with an external ID"""
        try:
            # List faces by external ID
            response = self.client.list_faces(
                CollectionId=self.collection_id,
                MaxResults=100
            )

            # Filter faces by external ID
            face_ids = [
                face['FaceId'] for face in response['Faces']
                if face['ExternalImageId'] == external_id
            ]

            if not face_ids:
                return True

            # Delete faces in batches of 100
            while face_ids:
                batch = face_ids[:100]
                self.client.delete_faces(
                    CollectionId=self.collection_id,
                    FaceIds=batch
                )
                face_ids = face_ids[100:]

            return True

        except ClientError as e:
            self.logger.error(f"AWS error deleting faces: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting faces: {str(e)}")
            return False 