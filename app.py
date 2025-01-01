import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
import requests
from PIL import Image
import io

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
HF_API_KEY = os.getenv('HF_API_KEY')
HF_API_URL = "https://api-inference.huggingface.co/models/xinntao/ESRGAN"

# Ensure the collection exists
def create_collection(collection_id):
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{collection_id}' already exists.")

create_collection(COLLECTION_ID)

def enhance_face_with_huggingface(face_image_bytes):
    """Enhance a cropped face using the Hugging Face API."""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(HF_API_URL, headers=headers, files={"image": ("face.jpg", face_image_bytes, "image/jpeg")})

    if response.status_code != 200:
        raise Exception(f"Hugging Face API error: {response.status_code}, {response.text}")

    return response.content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.form
        name = data.get('name')
        student_id = data.get('student_id')
        image = request.files.get('image')

        if not name or not student_id or not image:
            return jsonify({"message": "Missing name, student_id, or image"}), 400

        # Sanitize name
        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)

        # Convert image to bytes
        image_bytes = image.read()

        # Index the face in the Rekognition collection
        external_image_id = f"{sanitized_name}_{student_id}"
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            ExternalImageId=external_image_id,
            DetectionAttributes=['ALL'],
            QualityFilter='AUTO'
        )

        if not response['FaceRecords']:
            return jsonify({"message": "No face detected in the image"}), 400

        return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recognize', methods=['POST'])
def recognize():
    try:
        image = request.files.get('image')
        if not image:
            return jsonify({"message": "No image provided"}), 400

        # Read image bytes
        image_bytes = image.read()

        # Detect faces using AWS Rekognition
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )

        face_details = detect_response.get('FaceDetails', [])
        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200

        identified_people = []

        for face in face_details:
            # Crop face using bounding box
            bounding_box = face['BoundingBox']
            width, height = Image.open(io.BytesIO(image_bytes)).size
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)

            cropped_face = Image.open(io.BytesIO(image_bytes)).crop((left, top, right, bottom))
            cropped_face_bytes = io.BytesIO()
            cropped_face.save(cropped_face_bytes, format="JPEG")
            cropped_face_bytes = cropped_face_bytes.getvalue()

            # Enhance the cropped face
            try:
                enhanced_face_bytes = enhance_face_with_huggingface(cropped_face_bytes)
            except Exception as e:
                print(f"Face enhancement failed: {e}")
                continue

            # Recognize the enhanced face
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': enhanced_face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=60
            )

            face_matches = search_response.get('FaceMatches', [])
            if not face_matches:
                identified_people.append({"message": "Face not recognized"})
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
