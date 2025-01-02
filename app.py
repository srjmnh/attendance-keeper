import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
<<<<<<< HEAD
=======
from PIL import Image
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import io

app = Flask(__name__)

# AWS Rekognition configuration
# Fetch AWS credentials and configuration from environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
COLLECTION_ID = "students"
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

# Upscale image resolution using OpenCV
def upscale_image(image_bytes, upscale_factor=2):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    upscaled_image = cv2.resize(image, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
    _, upscaled_image_bytes = cv2.imencode('.jpg', upscaled_image)
    return upscaled_image_bytes.tobytes()
<<<<<<< HEAD

=======
# Split image into smaller regions for better face detection
def split_image(image, grid_size=2):
    width, height = image.size
    region_width = width // grid_size
    region_height = height // grid_size
    regions = []
    for row in range(grid_size):
        for col in range(grid_size):
            left = col * region_width
            top = row * region_height
            right = (col + 1) * region_width
            bottom = (row + 1) * region_height
            regions.append(image.crop((left, top, right, bottom)))
    return regions
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
<<<<<<< HEAD
        name = request.form.get('name')
        student_id = request.form.get('student_id')
=======
        data = request.form
        data = request.json
        name = data.get('name')
        student_id = data.get('student_id')
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
        image = request.files.get('image')
        image = data.get('image')

        if not name or not student_id or not image:
            return jsonify({"message": "Missing name, student_id, or image"}), 400

        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
        image_bytes = image.read()
        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        external_image_id = f"{sanitized_name}_{student_id}"
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            ExternalImageId=external_image_id,
            DetectionAttributes=['ALL'],
            QualityFilter='AUTO'
            QualityFilter='AUTO'  # Automatically handle low-quality images
        )

        if not response['FaceRecords']:
            return jsonify({"message": "No face detected in the image"}), 400

        return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recognize', methods=['POST'])
def recognize():
    try:
<<<<<<< HEAD
        image = request.files.get('image')

        if not image:
            return jsonify({"message": "No image provided"}), 400

        image_bytes = image.read()
        image_bytes = upscale_image(image_bytes)

=======
        print("Incoming request to /recognize")
        print(f"Request Content-Type: {request.content_type}")
        print(f"Request Files: {request.files}")
        # Check for 'image' in the request
        if 'image' not in request.files:
            print("No 'image' in request.files")
            return jsonify({"message": "No image part in the request"}), 400
        image = request.files['image']
        if image.filename == '':
            print("No image provided (empty filename)")
        data = request.json
        image = data.get('image')
        if not image:
            return jsonify({"message": "No image provided"}), 400

        # Convert image to bytes
        image_bytes = image.read()
        print(f"Image size: {len(image_bytes)} bytes")
        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Detect faces in the image
        print("Detecting faces with AWS Rekognition...")
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        # Step 1: Upscale image resolution
        image_bytes = upscale_image(image_bytes)
        # Enhance image (brightness and contrast)
        image = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # Increase contrast
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)  # Increase brightness

        face_details = detect_response.get('FaceDetails', [])
        face_count = len(face_details)
        print(f"{face_count} face(s) detected.")
        # Convert enhanced image back to bytes
        enhanced_image_bytes = io.BytesIO()
        image.save(enhanced_image_bytes, format="JPEG")
        enhanced_image_bytes = enhanced_image_bytes.getvalue()

        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200
        # Step 2: Split image into smaller regions
        regions = split_image(image, grid_size=2)

        identified_people = []
<<<<<<< HEAD
        for idx, face in enumerate(face_details):
=======
        face_count = 0

        for face in face_details:
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
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
<<<<<<< HEAD

=======
            # Perform face search
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': cropped_face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=60
        for region in regions:
            region_bytes = io.BytesIO()
            region.save(region_bytes, format="JPEG")
            region_bytes = region_bytes.getvalue()
            # Detect faces in the region
            detect_response = rekognition_client.detect_faces(
                Image={'Bytes': region_bytes},
                Attributes=['DEFAULT']
            )

            face_matches = search_response.get('FaceMatches', [])
            if not face_matches:
<<<<<<< HEAD
                identified_people.append({"message": "Face not recognized", "confidence": "N/A"})
=======
            face_details = detect_response.get('FaceDetails', [])
            face_count += len(face_details)
            # Process each detected face
            for face in face_details:
                bounding_box = face['BoundingBox']
                width, height = region.size
                left = int(bounding_box['Left'] * width)
                top = int(bounding_box['Top'] * height)
                right = int((bounding_box['Left'] + bounding_box['Width']) * width)
                bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)
                # Crop the face region
                cropped_face = region.crop((left, top, right, bottom))
                cropped_face_bytes = io.BytesIO()
                cropped_face.save(cropped_face_bytes, format="JPEG")
                cropped_face_bytes = cropped_face_bytes.getvalue()
                # Perform face search with lower FaceMatchThreshold
                search_response = rekognition_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': cropped_face_bytes},
                    MaxFaces=1,
                    FaceMatchThreshold=60  # Adjusted for better sensitivity
                )
                face_matches = search_response.get('FaceMatches', [])
                if not face_matches:
                    identified_people.append({
                        "message": "Face not recognized",
                        "confidence": "N/A"
                    })
                    continue
                # Extract the best match
                match = face_matches[0]
                external_image_id = match['Face']['ExternalImageId']
                confidence = match['Face']['Confidence']
                # Safely parse the external_image_id
                parts = external_image_id.split("_")
                if len(parts) == 2:
                    name, student_id = parts
                else:
                    name, student_id = external_image_id, "Unknown"
                identified_people.append({
                    "message": "Face not recognized",
                    "confidence": "N/A"
                    "name": name,
                    "student_id": student_id,
                    "confidence": confidence
                })
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
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
        print(f"Error during recognition: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
<<<<<<< HEAD
    port = int(os.getenv('PORT', 5000))
=======
    port = int(os.getenv('PORT', 5000))  # Default port for Flask
    port = int(os.getenv('PORT', 5000))  # Use PORT from environment or default to 5000
>>>>>>> 93a0387e99d5d165ac2d1f0265d46472cae851b7
    app.run(host='0.0.0.0', port=port)
    