import boto3
import base64
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# AWS Rekognition client setup
rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id='YOUR_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='YOUR_AWS_SECRET_ACCESS_KEY',
    region_name='YOUR_AWS_REGION'
)

COLLECTION_ID = "students"  # AWS Rekognition Collection name

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

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Index the face in the Rekognition collection
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            ExternalImageId=f"{name}_{student_id}",
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

        # Search for the face in the Rekognition collection
        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80
        )

        face_matches = response.get('FaceMatches', [])
        if not face_matches:
            return jsonify({"message": "No matching face found"}), 200

        # Extract matched face information
        match = face_matches[0]
        external_image_id = match['Face']['ExternalImageId']
        confidence = match['Face']['Confidence']

        # Extract name and student_id from ExternalImageId
        name, student_id = external_image_id.split("_")

        return jsonify({
            "message": "Face recognized",
            "name": name,
            "student_id": student_id,
            "confidence": confidence
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)