import io
import uuid
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

# Constants for security & performance
MAX_IMAGE_SIZE = (800, 800)  # Maximum (width, height) in pixels
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png"}  # Allowed formats
MAX_FILE_SIZE_MB = 5  # Maximum allowed file size in MB

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
    """
    try:
        # Ensure file is within size limits
        file_size_mb = image.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large: {file_size_mb:.2f}MB. Max size is {MAX_FILE_SIZE_MB}MB.")

        # Open the image using PIL
        image.seek(0)  # Reset file pointer
        img = Image.open(image)

        # Check if the image is corrupt
        img.verify()
        image.seek(0)  # Reset again after verification
        img = Image.open(image)  # Reopen to process

        # Validate format (strict check)
        if img.format not in ALLOWED_FORMATS:
            raise ValueError(f"Invalid format: {img.format}. Allowed formats: {', '.join(ALLOWED_FORMATS.keys())}")

        # Convert to RGB (removes transparency & ensures compatibility)
        img = img.convert("RGB")

        # Resize while maintaining aspect ratio
        img.thumbnail(max_size, Image.ANTIALIAS)

        # Save to memory with compression
        output = io.BytesIO()
        format_ = "JPEG"  # Always save as JPEG for consistency
        img.save(output, format=format_, quality=quality)
        output.seek(0)

        # Generate a unique filename
        ext = format_.lower()
        filename = f"{uuid.uuid4()}.{ext}"

        # Return InMemoryUploadedFile (ready for database storage)
        return InMemoryUploadedFile(
            output, "ImageField", filename, ALLOWED_FORMATS[format_], output.getbuffer().nbytes, None
        )

    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")
