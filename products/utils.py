import io
import os
import time
from PIL import Image, UnidentifiedImageError
from PIL.Image import Resampling
from django.core.files.uploadedfile import InMemoryUploadedFile

# Constants for security & performance
MAX_IMAGE_SIZE = (800, 800)  # Maximum (width, height) in pixels
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif", "WEBP": "image/webp"}  # Allowed formats
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # Maximum allowed file size in bytes (5MB)

def process_image(image, max_size=MAX_IMAGE_SIZE, quality=85):
    """
    Processes an uploaded image:
    - Validates format (JPEG/PNG only)
    - Detects corrupt or fake images
    - Resizes and compresses to optimize performance
    - Returns an InMemoryUploadedFile ready for storage

    Parameters:
    - image (InMemoryUploadedFile): The uploaded image file
    - max_size (tuple): Maximum allowed size (width, height)
    - quality (int): Compression quality (default: 85)

    Returns:
    - InMemoryUploadedFile: The processed image file

    Raises:
    - ValueError: If the image is invalid, too large, or processing fails
    """
    try:
        # Ensure file is within size limits
        if image.size > MAX_FILE_SIZE_BYTES:
            file_size_mb = image.size / (1024 * 1024)
            max_size_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            raise ValueError(f"File too large: {file_size_mb:.2f}MB. Max size is {max_size_mb:.2f}MB.")
        # Open the image using PIL
        image.seek(0)  # Reset file pointer
        try:
            img = Image.open(image)
        except UnidentifiedImageError:
            raise ValueError("Invalid or unsupported image format.")

        # Check if the image is corrupt or truncated
        try:
            img.verify()  # Verify integrity
            image.seek(0)  # Reset file pointer after verify()
            img = Image.open(image)  # Reopen to fully load
            img.load()  # Now load without issues
        except Exception as e:
            raise ValueError(f"Corrupt or invalid image: {str(e)}")

        # Validate format (strict check)
        if img.format not in ALLOWED_FORMATS:
            raise ValueError(f"Invalid format: {img.format}. Allowed formats: {', '.join(ALLOWED_FORMATS.keys())}")

        # Convert to RGB (removes transparency & ensures compatibility)
        if img.mode in ("RGBA", "P"):  
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Apply alpha mask
            img = background
        
        # Convert to RGB (ensures compatibility)
        img = img.convert("RGB")

        # Resize while maintaining aspect ratio
        img.thumbnail(max_size, Resampling.LANCZOS) 

        # Save to memory with compression
        output = io.BytesIO()
        format_ = img.format if img.format in ALLOWED_FORMATS else "JPEG"
        img.save(output, format=format_, quality=quality)
        output.seek(0)

        # Generate a unique filename
        filename = f"{get_unique_filename(image.name)}"

        # Return InMemoryUploadedFile (ready for database storage)
        return InMemoryUploadedFile(
            output, "ImageField", filename, ALLOWED_FORMATS[format_], output.getbuffer().nbytes, None
        )

    except Exception as e:
        # Close any open file handles
        if 'img' in locals():
            img.close()
        if 'output' in locals():
            output.close()
        raise ValueError(f"Image processing failed: {str(e)}")
    

def get_unique_filename(original_filename):
    name, ext = os.path.splitext(original_filename)  # Extract name and extension
    timestamp = int(time.time())  # Use current timestamp for uniqueness
    return f"{name}_{timestamp}{ext}"  # Example: "image_1678901234.jpg"
