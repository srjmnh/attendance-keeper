import os
import cv2
import numpy as np
from PIL import Image
import logging
from werkzeug.utils import secure_filename
from datetime import datetime

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self, upload_folder):
        """Initialize image service"""
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def save_image(self, image_file, prefix='img'):
        """Save uploaded image and return path"""
        try:
            if image_file:
                # Generate secure filename with timestamp
                filename = secure_filename(image_file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                new_filename = f"{prefix}_{timestamp}_{filename}"
                
                # Save the file
                filepath = os.path.join(self.upload_folder, new_filename)
                image_file.save(filepath)
                
                logger.info(f"Saved image: {filepath}")
                return filepath
            return None
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            raise

    def read_image_bytes(self, filepath):
        """Read image file and return bytes"""
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading image bytes: {str(e)}")
            raise

    def process_image(self, filepath, max_size=1024):
        """Process image for face recognition"""
        try:
            # Read image
            image = cv2.imread(filepath)
            if image is None:
                raise ValueError("Failed to read image")

            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Resize if needed
            height, width = image_rgb.shape[:2]
            if height > max_size or width > max_size:
                scale = max_size / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image_rgb = cv2.resize(image_rgb, (new_width, new_height))

            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)

            # Save processed image
            processed_path = filepath.replace('.', '_processed.')
            pil_image.save(processed_path, quality=95)

            logger.info(f"Processed image saved: {processed_path}")
            return processed_path

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    def detect_faces(self, filepath):
        """Detect faces in image using OpenCV"""
        try:
            # Read image
            image = cv2.imread(filepath)
            if image is None:
                raise ValueError("Failed to read image")

            # Load face cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)

            # Save marked image
            marked_path = filepath.replace('.', '_marked.')
            cv2.imwrite(marked_path, image)

            logger.info(f"Detected {len(faces)} faces in image")
            return {
                'face_count': len(faces),
                'marked_image_path': marked_path,
                'face_locations': faces.tolist()
            }

        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}")
            raise

    def cleanup_old_images(self, max_age_hours=24):
        """Clean up old processed images"""
        try:
            current_time = datetime.utcnow()
            count = 0
            
            for filename in os.listdir(self.upload_folder):
                filepath = os.path.join(self.upload_folder, filename)
                
                # Skip if not a file
                if not os.path.isfile(filepath):
                    continue
                
                # Get file creation time
                creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                age_hours = (current_time - creation_time).total_seconds() / 3600
                
                # Delete if older than max age
                if age_hours > max_age_hours:
                    os.remove(filepath)
                    count += 1
            
            logger.info(f"Cleaned up {count} old images")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up images: {str(e)}")
            raise 