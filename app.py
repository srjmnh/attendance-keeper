import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
from PIL import Image
import io

app = Flask(__name__)

# AWS credentials and configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
COLLECTION_ID = "students"  # Rekognition Collection name

# Initialize AWS Rekognition client
rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Ensure the collection exists
def create_collection(collection_id):
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{collection_id}' already exists.")

create_collection(COLLECTION_ID)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        name = data.get('name')
        student_id = data.get('student_id')
        image = data.get('image')

        if not name or not student_id or not image:
            return jsonify({"message": "Missing name, student_id, or image"}), 400

        # Sanitize name
        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

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
        data = request.json
        image = data.get('image')

        if not image:
            print("No image provided in the request.")
            return jsonify({"message": "No image provided"}), 400

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Detect faces in the image
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )

        face_details = detect_response.get('FaceDetails', [])
        face_count = len(face_details)

        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200

        identified_people = []

        for face in face_details:
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

            # Perform face search
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': cropped_face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=60
            )

            face_matches = search_response.get('FaceMatches', [])
            if not face_matches:
                identified_people.append({
                    "message": "Face not recognized",
                    "confidence": "N/A"
                })
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
            "message": f"{face_count} face(s) detected in the photo.",
            "total_faces": face_count,
            "identified_people": identified_people
        }), 200

    except Exception as e:
        print("Error during recognition:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Default port for Flask
    app.run(host='0.0.0.0', port=port)