import boto3
import base64
import os
from flask import Flask, request, jsonify, render_template
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import io

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

# Enhance image with super-resolution
def upscale_image(image_bytes, upscale_factor=2):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    upscaled_image = cv2.resize(image, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
    _, upscaled_image_bytes = cv2.imencode('.jpg', upscaled_image)
    return upscaled_image_bytes.tobytes()

# Reduce noise in the image
def denoise_image(image_bytes):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    denoised_image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    _, denoised_image_bytes = cv2.imencode('.jpg', denoised_image)
    return denoised_image_bytes.tobytes()

# Enhance image contrast
def equalize_image(image_bytes):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    enhanced_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    _, enhanced_image_bytes = cv2.imencode('.jpg', enhanced_image)
    return enhanced_image_bytes.tobytes()

# Split image into smaller regions
def split_image(image, grid_size=3):
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
        data = request.json
        image = data.get('image')

        if not image:
            return jsonify({"message": "No image provided"}), 400

        # Decode base64 image
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Step 1: Enhance image (super-resolution, denoising, and contrast)
        image_bytes = upscale_image(image_bytes)  # Super-resolution
        image_bytes = denoise_image(image_bytes)  # Noise reduction
        image_bytes = equalize_image(image_bytes)  # Contrast enhancement

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

        # Step 2: Split image into smaller regions
        regions = split_image(image, grid_size=3)

        identified_people = []
        face_count = 0

        for region in regions:
            region_bytes = io.BytesIO()
            region.save(region_bytes, format="JPEG")
            region_bytes = region_bytes.getvalue()

            # Detect faces in the region
            detect_response = rekognition_client.detect_faces(
                Image={'Bytes': region_bytes},
                Attributes=['ALL']
            )

            face_details = detect_response.get('FaceDetails', [])
            face_count += len(face_details)

            for face in face_details:
                bounding_box = face['BoundingBox']
                width, height = region.size
                left = int(bounding_box['Left'] * width)
                top = int(bounding_box['Top'] * height)
                right = int((bounding_box['Left'] + bounding_box['Width']) * width)
                bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)

                cropped_face = region.crop((left, top, right, bottom))
                cropped_face_bytes = io.BytesIO()
                cropped_face.save(cropped_face_bytes, format="JPEG")
                cropped_face_bytes = cropped_face_bytes.getvalue()

                # Perform face search with lower FaceMatchThreshold
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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Use PORT from environment or default to 5000
    app.run(host='0.0.0.0', port=port)
