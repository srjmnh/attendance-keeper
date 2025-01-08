from firebase_admin import storage
from flask import current_app
import tempfile
import os

def upload_file(file_obj, destination_path):
    """Upload a file to Firebase Storage
    
    Args:
        file_obj: File object from request.files
        destination_path: Path where the file should be stored in Firebase Storage
        
    Returns:
        str: Public URL of the uploaded file
    """
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_obj.save(temp_file.name)
            
            # Get storage bucket
            bucket = storage.bucket()
            
            # Create blob and upload file
            blob = bucket.blob(destination_path)
            blob.upload_from_filename(temp_file.name)
            
            # Make the blob publicly accessible
            blob.make_public()
            
            # Clean up temporary file
            os.unlink(temp_file.name)
            
            return blob.public_url
            
    except Exception as e:
        current_app.logger.error(f"File upload error: {str(e)}")
        raise

def delete_file(file_url):
    """Delete a file from Firebase Storage
    
    Args:
        file_url: Public URL of the file to delete
    """
    try:
        # Get storage bucket
        bucket = storage.bucket()
        
        # Extract blob path from URL
        blob_path = file_url.split(f"{bucket.name}.appspot.com/")[1]
        
        # Get and delete blob
        blob = bucket.blob(blob_path)
        blob.delete()
        
    except Exception as e:
        current_app.logger.error(f"File deletion error: {str(e)}")
        raise

def get_file_url(file_path):
    """Get the public URL of a file in Firebase Storage
    
    Args:
        file_path: Path of the file in Firebase Storage
        
    Returns:
        str: Public URL of the file
    """
    try:
        # Get storage bucket
        bucket = storage.bucket()
        
        # Get blob
        blob = bucket.blob(file_path)
        
        # Make the blob publicly accessible if it isn't already
        if not blob.public_url:
            blob.make_public()
        
        return blob.public_url
        
    except Exception as e:
        current_app.logger.error(f"Error getting file URL: {str(e)}")
        raise

def copy_file(source_path, destination_path):
    """Copy a file within Firebase Storage
    
    Args:
        source_path: Path of the source file
        destination_path: Path where the file should be copied to
        
    Returns:
        str: Public URL of the copied file
    """
    try:
        # Get storage bucket
        bucket = storage.bucket()
        
        # Get source blob
        source_blob = bucket.blob(source_path)
        
        # Copy to new location
        new_blob = bucket.copy_blob(
            source_blob, bucket, destination_path
        )
        
        # Make the new blob publicly accessible
        new_blob.make_public()
        
        return new_blob.public_url
        
    except Exception as e:
        current_app.logger.error(f"File copy error: {str(e)}")
        raise

def move_file(source_path, destination_path):
    """Move a file within Firebase Storage
    
    Args:
        source_path: Path of the source file
        destination_path: Path where the file should be moved to
        
    Returns:
        str: Public URL of the moved file
    """
    try:
        # Copy file to new location
        new_url = copy_file(source_path, destination_path)
        
        # Delete original file
        bucket = storage.bucket()
        source_blob = bucket.blob(source_path)
        source_blob.delete()
        
        return new_url
        
    except Exception as e:
        current_app.logger.error(f"File move error: {str(e)}")
        raise 