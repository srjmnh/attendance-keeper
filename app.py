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

    print("Enhancement successful. Returning enhanced image.")
    return response.content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize():
    try:
        print("Incoming request to /recognize")
        print(f"Request Files: {request.files}")

        # Check if image is provided
        image = request.files.get('image')
        if not image:
            print("No image provided in request.files")
            return jsonify({"message": "No image provided"}), 400

        # Read image bytes
        image_bytes = image.read()
        print(f"Image received. Size: {len(image_bytes)} bytes")

        # Enhance the entire image
        try:
            enhanced_image_bytes = enhance_image_with_huggingface(image_bytes)
            print("Image enhancement completed.")
        except Exception as e:
            print(f"Image enhancement failed: {e}")
            return jsonify({"message": "Image enhancement failed"}), 500

        # Save enhanced image for debugging
        with open("debug_enhanced_image.jpg", "wb") as f:
            f.write(enhanced_image_bytes)

        # Detect faces using AWS Rekognition
        print("Detecting faces with AWS Rekognition...")
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )
        print(f"Rekognition response: {detect_response}")

        face_details = detect_response.get('FaceDetails', [])
        if not face_details:
            return jsonify({"message": "No faces detected", "total_faces": 0}), 200

        identified_people = []

        for idx, face in enumerate(face_details):
            bounding_box = face['BoundingBox']
            width, height = Image.open(io.BytesIO(enhanced_image_bytes)).size
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)

            # Crop face and save for debugging
            cropped_face = Image.open(io.BytesIO(enhanced_image_bytes)).crop((left, top, right, bottom))
            cropped_face_bytes = io.BytesIO()
            cropped_face.save(cropped_face_bytes, format="JPEG")
            cropped_face_bytes = cropped_face_bytes.getvalue()

            # Save cropped face for debugging
            with open(f"debug_cropped_face_{idx}.jpg", "wb") as f:
                f.write(cropped_face_bytes)

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