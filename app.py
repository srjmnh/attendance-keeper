import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
import requests
from PIL import Image, ImageEnhance
import io
import cv2
import numpy as np

app = Flask(__name__)

# AWS Rekognition configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
COLLECTION_ID = "students"

rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Hugging Face API configuration
HF_API_URL = "https://api-inference.huggingface.co/models/xinntao/ESRGAN"
HF_API_KEY = os.getenv('HF_API_KEY')  # Ensure this is set in the environment

# Ensure the collection exists
def create_collection(collection_id):
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{collection_id}' already exists.")

create_collection(COLLECTION_ID)

def enhance_image_with_huggingface(image_bytes):
    """Enhance the entire image using Hugging Face API."""
    if not HF_API_KEY:
        raise Exception("HF_API_KEY environment variable is not set!")

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            files={"image": ("input.jpg", image_bytes, "image/jpeg")},
            timeout=30  # Adding timeout for robustness
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Hugging Face API error: {e}")
        raise Exception(f"Error enhancing image with Hugging Face API: {e}")

    if not response.content:
        raise Exception("No content in the response from Hugging Face API")

    return response.content

def enhance_image_locally(image_bytes):
    """Enhance image quality using local methods."""
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Apply sharpening kernel
        kernel = np.array([[0, -1, 0],
                           [-1, 5,-1],
                           [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)

        # Convert back to bytes
        _, buffer = cv2.imencode('.jpg', img)
        return buffer.tobytes()
    except Exception as e:
        print(f"Local image enhancement error: {e}")
        return image_bytes  # Return original if enhancement fails

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize():
    try:
        image = request.files.get('image')
        if not image:
            return jsonify({"message": "No image provided"}), 400

        # Read image bytes
        image_bytes = image.read()

        # Enhance the entire image
        try:
            enhanced_image_bytes = enhance_image_with_huggingface(image_bytes)
            print("Image enhancement completed.")
        except Exception as e:
            print(f"Image enhancement failed: {e}")
            # Fallback to local enhancement
            enhanced_image_bytes = enhance_image_locally(image_bytes)

        # Detect faces using AWS Rekognition
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )

        face_details = detect_response.get('FaceDetails', [])
        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200

        identified_people = []

        for idx, face in enumerate(face_details):
            # Crop face using bounding box
            bounding_box = face['BoundingBox']
            width, height = Image.open(io.BytesIO(enhanced_image_bytes)).size
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)

            cropped_face = Image.open(io.BytesIO(enhanced_image_bytes)).crop((left, top, right, bottom))
            cropped_face_bytes = io.BytesIO()
            cropped_face.save(cropped_face_bytes, format="JPEG")
            cropped_face_bytes = cropped_face_bytes.getvalue()

            # Recognize the cropped face
            try:
                search_response = rekognition_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': cropped_face_bytes},
                    MaxFaces=1,
                    FaceMatchThreshold=60
                )
            except Exception as e:
                print(f"Face recognition failed for face {idx}: {e}")
                continue

            face_matches = search_response.get('FaceMatches', [])
            if not face_matches:
                identified_people.append({"message": f"Face {idx + 1} not recognized"})
                continue

            match = face_matches[0]
            external_image_id = match['Face']['ExternalImageId']
            confidence = match['Face']['Confidence']

            parts = external_image_id.split("_")
            name, student_id = parts if len(parts) == 2 else (external_image_id, "Unknown")

            identified_people.append({
                "name": name,
                "student_id": student_id,
                "confidence": confidence
            })

        return jsonify({
            "message": f"{len(face_details)} face(s) detected in the photo.",
            "identified_people": identified_people
        }), 200

    except Exception as e:
        print(f"Error during recognition: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Default port for Flask
    app.run(host='0.0.0.0', port=port)
    