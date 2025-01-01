import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Fetch AWS credentials and configuration from environment variables
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
            DetectionAttributes=['ALL']
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
            return jsonify({"message": "No image provided"}), 400

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Step 1: Detect all faces in the image
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['DEFAULT']
        )

        face_details = detect_response.get('FaceDetails', [])
        face_count = len(face_details)

        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0, "identified_people": []}), 200

        # Step 2: Process each detected face individually
        identified_people = []
        for i, face in enumerate(face_details):
            # Perform face search for the detected face
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': image_bytes},
                MaxFaces=1,
                FaceMatchThreshold=80
            )

            face_matches = search_response.get('FaceMatches', [])
            if not face_matches:
                identified_people.append({
                    "face_number": i + 1,
                    "message": f"Face {i + 1} not recognized",
                    "confidence": "N/A"
                })
                continue

            # Extract the best match
            match = face_matches[0]
            external_image_id = match['Face']['ExternalImageId']
            confidence = match['Face']['Confidence']

            # Parse name and student ID from ExternalImageId
            if "_" in external_image_id:
                name, student_id = external_image_id.split("_")
            else:
                name, student_id = external_image_id, "Unknown"

            identified_people.append({
                "face_number": i + 1,
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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Use PORT from environment or default to 5000
    app.run(host='0.0.0.0', port=port)