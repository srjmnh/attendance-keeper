import boto3
import base64
import logging
from botocore.exceptions import ClientError
from .image_service import ImageService

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self, aws_access_key_id, aws_secret_access_key, aws_region, collection_id):
        """Initialize AWS Rekognition client"""
        self.collection_id = collection_id
        self.client = boto3.client(
            'rekognition',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Ensure the face collection exists"""
        try:
            self.client.describe_collection(CollectionId=self.collection_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.client.create_collection(CollectionId=self.collection_id)
            else:
                raise

    def register_face(self, image_data, external_image_id):
        """
        Register a face in the collection
        :param image_data: Base64 encoded image or bytes
        :param external_image_id: External ID to associate with the face
        :return: Face ID if successful
        """
        try:
            # Process image if it's base64 encoded
            if isinstance(image_data, str):
                image = ImageService.process_base64_image(image_data)
                image_bytes = ImageService.get_image_bytes(image)
            else:
                image_bytes = image_data

            # Index face
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=external_image_id,
                MaxFaces=1,
                QualityFilter='AUTO',
                DetectionAttributes=['ALL']
            )

            if not response['FaceRecords']:
                raise ValueError('No face detected in the image')

            return response['FaceRecords'][0]['Face']['FaceId']

        except ClientError as e:
            logger.error(f"Error registering face: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    def recognize_faces(self, image_data, min_confidence=80):
        """
        Recognize faces in an image
        :param image_data: Base64 encoded image or bytes
        :param min_confidence: Minimum confidence threshold (0-100)
        :return: Dict with recognition results
        """
        try:
            # Process image if it's base64 encoded
            if isinstance(image_data, str):
                image = ImageService.process_base64_image(image_data)
                image_bytes = ImageService.get_image_bytes(image)
            else:
                image_bytes = image_data

            # Detect faces
            detect_response = self.client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )

            total_faces = len(detect_response['FaceDetails'])
            if total_faces == 0:
                return {
                    'total_faces': 0,
                    'identified_people': [],
                    'unidentified_faces': 0
                }

            # Search for each detected face
            identified_people = []
            unidentified_faces = 0

            # Search faces
            search_response = self.client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=total_faces,
                FaceMatchThreshold=min_confidence
            )

            # Process matches
            face_matches = search_response.get('FaceMatches', [])
            for match in face_matches:
                face = match['Face']
                if match['Similarity'] >= min_confidence:
                    # Extract student info from external image id
                    name, student_id = face['ExternalImageId'].split('_')
                    identified_people.append({
                        'face_id': face['FaceId'],
                        'student_id': student_id,
                        'name': name,
                        'confidence': match['Similarity'],
                        'bounding_box': match['Face']['BoundingBox']
                    })
                else:
                    unidentified_faces += 1

            return {
                'total_faces': total_faces,
                'identified_people': identified_people,
                'unidentified_faces': unidentified_faces
            }

        except ClientError as e:
            logger.error(f"Error recognizing faces: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    def delete_face(self, face_id):
        """
        Delete a face from the collection
        :param face_id: Face ID to delete
        """
        try:
            self.client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting face: {str(e)}")
            raise

    def list_faces(self, max_results=100):
        """
        List all faces in the collection
        :param max_results: Maximum number of faces to return
        :return: List of faces
        """
        try:
            faces = []
            paginator = self.client.get_paginator('list_faces')
            
            for page in paginator.paginate(
                CollectionId=self.collection_id,
                MaxResults=max_results
            ):
                faces.extend(page['Faces'])
                if len(faces) >= max_results:
                    break

            return faces[:max_results]

        except ClientError as e:
            logger.error(f"Error listing faces: {str(e)}")
            raise

    def get_face_info(self, face_id):
        """
        Get information about a specific face
        :param face_id: Face ID to get info for
        :return: Face information
        """
        try:
            response = self.client.describe_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            
            if not response['Faces']:
                return None
                
            return response['Faces'][0]

        except ClientError as e:
            logger.error(f"Error getting face info: {str(e)}")
            raise

    def compare_faces(self, source_image, target_image, similarity_threshold=80):
        """
        Compare faces between two images
        :param source_image: Source image (base64 or bytes)
        :param target_image: Target image (base64 or bytes)
        :param similarity_threshold: Minimum similarity threshold (0-100)
        :return: List of face matches
        """
        try:
            # Process images if they're base64 encoded
            if isinstance(source_image, str):
                source_image = ImageService.process_base64_image(source_image)
                source_bytes = ImageService.get_image_bytes(source_image)
            else:
                source_bytes = source_image

            if isinstance(target_image, str):
                target_image = ImageService.process_base64_image(target_image)
                target_bytes = ImageService.get_image_bytes(target_image)
            else:
                target_bytes = target_image

            response = self.client.compare_faces(
                SourceImage={'Bytes': source_bytes},
                TargetImage={'Bytes': target_bytes},
                SimilarityThreshold=similarity_threshold
            )

            return response['FaceMatches']

        except ClientError as e:
            logger.error(f"Error comparing faces: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing images: {str(e)}")
            raise 