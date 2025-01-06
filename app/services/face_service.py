import os
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self, collection_id='student-faces'):
        """Initialize AWS Rekognition client"""
        self.client = boto3.client('rekognition',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.collection_id = collection_id
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Ensure the face collection exists"""
        try:
            self.client.describe_collection(CollectionId=self.collection_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.client.create_collection(CollectionId=self.collection_id)
                logger.info(f"Created collection: {self.collection_id}")
            else:
                logger.error(f"Error checking collection: {str(e)}")
                raise

    def register_face(self, image_bytes, external_id):
        """Register a face in the collection"""
        try:
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=external_id,
                MaxFaces=1,
                QualityFilter="AUTO",
                DetectionAttributes=['ALL']
            )

            if not response['FaceRecords']:
                logger.warning(f"No face detected in the image for {external_id}")
                return None

            face_id = response['FaceRecords'][0]['Face']['FaceId']
            logger.info(f"Registered face {face_id} for {external_id}")
            return face_id

        except Exception as e:
            logger.error(f"Error registering face: {str(e)}")
            raise

    def recognize_faces(self, image_bytes, max_faces=10):
        """Recognize faces in an image"""
        try:
            response = self.client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=max_faces,
                FaceMatchThreshold=80
            )

            matches = []
            for match in response['FaceMatches']:
                matches.append({
                    'external_id': match['Face']['ExternalImageId'],
                    'confidence': match['Similarity'],
                    'face_id': match['Face']['FaceId']
                })

            logger.info(f"Found {len(matches)} face matches")
            return matches

        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidParameterException':
                logger.warning("No faces detected in the image")
                return []
            logger.error(f"Error recognizing faces: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error recognizing faces: {str(e)}")
            raise

    def delete_face(self, face_id):
        """Delete a face from the collection"""
        try:
            self.client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            logger.info(f"Deleted face {face_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting face: {str(e)}")
            raise

    def list_faces(self):
        """List all faces in the collection"""
        try:
            response = self.client.list_faces(CollectionId=self.collection_id)
            faces = []
            for face in response['Faces']:
                faces.append({
                    'face_id': face['FaceId'],
                    'external_id': face['ExternalImageId'],
                    'confidence': face['Confidence'],
                    'timestamp': face['Timestamp']
                })
            return faces
        except Exception as e:
            logger.error(f"Error listing faces: {str(e)}")
            raise

    def delete_collection(self):
        """Delete the face collection"""
        try:
            self.client.delete_collection(CollectionId=self.collection_id)
            logger.info(f"Deleted collection: {self.collection_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise 