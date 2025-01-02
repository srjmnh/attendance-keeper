import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
from PIL import Image, ImageEnhance
import tensorflow as tf
import cv2
import numpy as np
import io

app = Flask(__name__)

# AWS Rekognition configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
COLLECTION_ID = "students"  # Rekognition Collection name

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

# Enhance image using TensorFlow EDSR
def upscale_image_with_edsr(image_bytes, model_path="models/EDSR_x4.pb"):
    # Load the pre-trained EDSR model
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"EDSR model not found at {model_path}")

    # Decode the input image
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # Prepare the input for the model
    input_image = tf.convert_to_tensor(img, dtype=tf.float32)
    input_image = tf.image.resize(input_image, [img.shape[0], img.shape[1]])
    input_image = tf.expand_dims(input_image, axis=0)

    # Predict the upscaled image
    model = tf.saved_model.load(model_path)
    upscaled_image = model(input_image)
    upscaled_image = tf.squeeze(upscaled_image, axis=0).numpy()

    # Convert back to bytes
    _, upscaled_image_bytes = cv2.imencode('.jpg', upscaled_image)
    return upscaled_image_bytes.tobytes()

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
            return jsonify({"message": "No image provided"}), 400

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Step 1: Enhance image using TensorFlow EDSR
        image_bytes = upscale_image_with_edsr(image_bytes)

        # Enhance image for brightness and contrast
        image = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)

        # Convert enhanced image back to bytes
        enhanced_image_bytes = io.BytesIO()
        image.save(enhanced_image_bytes, format="JPEG")
        enhanced_image_bytes = enhanced_image_bytes.getvalue()

        # Step 2: Detect faces
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )

        face_details = detect_response.get('FaceDetails', [])
        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200

        identified_people = []

        for face in face_details:
            bounding_box = face['BoundingBox']
            width, height = image.size
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)
            cropped_face = image.crop((left, top, right, bottom))
            cropped_face_bytes = io.BytesIO()
            cropped_face.save(cropped_face_bytes, format="JPEG")
            cropped_face_bytes = cropped_face_bytes.getvalue()

            # Perform face search with lower FaceMatchThreshold
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': cropped_face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=50  # Lower threshold for guesses
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
            "message": f"{len(face_details)} face(s) detected in the photo.",
            "total_faces": len(face_details),
            "identified_people": identified_people
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
