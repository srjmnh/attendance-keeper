import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
import base64

class ImageService:
    @staticmethod
    def enhance_image(pil_image):
        """
        Enhance image quality to improve face detection in distant group photos.
        Uses both PIL and OpenCV for comprehensive image processing.
        """
        # First apply PIL enhancements
        pil_enhanced = ImageService._apply_pil_enhancements(pil_image)
        
        # Convert PIL image to OpenCV format
        cv_image = cv2.cvtColor(np.array(pil_enhanced), cv2.COLOR_RGB2BGR)

        # Apply OpenCV enhancements
        enhanced = ImageService._apply_opencv_enhancements(cv_image)

        # Convert back to PIL Image
        enhanced_pil = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
        
        # Final PIL adjustments
        enhanced_pil = ImageService._final_pil_adjustments(enhanced_pil)
        
        return enhanced_pil

    @staticmethod
    def _apply_pil_enhancements(image):
        """
        Apply PIL-based enhancements
        """
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)  # Increase contrast by 30%

        # Enhance brightness
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)  # Increase brightness by 10%

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)  # Increase sharpness by 50%

        return image

    @staticmethod
    def _apply_opencv_enhancements(image):
        """
        Apply OpenCV-based enhancements
        """
        # Convert to LAB color space for better processing
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)

        # Merge the CLAHE enhanced L-channel back with A and B channels
        limg = cv2.merge((cl,a,b))

        # Convert back to BGR color space
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # Adjust brightness and contrast
        alpha = 1.2  # Contrast control (1.0-3.0)
        beta = 10    # Brightness control (0-100)
        enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)

        # Reduce noise while preserving edges
        enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)

        return enhanced

    @staticmethod
    def _final_pil_adjustments(image):
        """
        Apply final PIL adjustments for optimal face detection
        """
        # Fine-tune color
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)  # Slightly enhance color

        return image

    @staticmethod
    def process_base64_image(base64_string):
        """
        Process base64 image string and return enhanced PIL Image
        """
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        # Decode base64 string
        image_bytes = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Enhance image
        enhanced_image = ImageService.enhance_image(image)
        
        return enhanced_image

    @staticmethod
    def get_image_bytes(image, format='JPEG'):
        """
        Convert PIL Image to bytes
        """
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=format)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    @staticmethod
    def get_base64_string(image, format='JPEG'):
        """
        Convert PIL Image to base64 string
        """
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=format)
        img_byte_arr.seek(0)
        return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8') 