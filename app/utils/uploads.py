"""
File upload utilities for Ngenda Hotel PMS.
Handles room images, documents, and other uploads.
"""
import os
import uuid
from werkzeug.utils import secure_filename

# Allowed extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}

# Upload folders (relative to app root)
UPLOAD_FOLDERS = {
    'rooms': 'app/static/uploads/rooms',
    'gallery': 'app/static/uploads/gallery',
    'logos': 'app/static/uploads/logos',
    'documents': 'app/static/uploads/documents',
}


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def generate_unique_filename(original_filename, prefix=''):
    """Generate a unique filename while preserving extension."""
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = uuid.uuid4().hex[:12]
    safe_name = secure_filename(original_filename.rsplit('.', 1)[0])[:50]
    return f"{prefix}{safe_name}_{unique_id}.{ext}"


def save_upload(file, upload_type='rooms', prefix=''):
    """
    Save an uploaded file to the appropriate folder.
    
    Args:
        file: FileStorage object from Flask request
        upload_type: One of 'rooms', 'gallery', 'logos', 'documents'
        prefix: Optional prefix for the filename
    
    Returns:
        Filename if successful, None if failed
    """
    if not file or file.filename == '':
        return None
    
    # Determine allowed extensions based on upload type
    if upload_type in ('rooms', 'gallery', 'logos'):
        allowed_exts = ALLOWED_IMAGE_EXTENSIONS
    else:
        allowed_exts = ALLOWED_DOCUMENT_EXTENSIONS
    
    if not allowed_file(file.filename, allowed_exts):
        return None
    
    # Generate unique filename
    filename = generate_unique_filename(file.filename, prefix)
    
    # Get upload folder
    upload_folder = UPLOAD_FOLDERS.get(upload_type, UPLOAD_FOLDERS['rooms'])
    
    # Ensure folder exists
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save file
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    return filename


def save_room_image(file, room_type_id=None):
    """Save a room image and return the filename."""
    prefix = f"room_{room_type_id}_" if room_type_id else "room_"
    return save_upload(file, upload_type='rooms', prefix=prefix)


def save_gallery_image(file):
    """Save a gallery image and return the filename."""
    return save_upload(file, upload_type='gallery', prefix='gallery_')


def save_logo(file, hotel_id=None):
    """Save a hotel logo and return the filename."""
    prefix = f"logo_{hotel_id}_" if hotel_id else "logo_"
    return save_upload(file, upload_type='logos', prefix=prefix)


def save_document(file):
    """Save a document and return the filename."""
    return save_upload(file, upload_type='documents', prefix='doc_')


def delete_file(filename, upload_type='rooms'):
    """Delete a file from the uploads folder."""
    upload_folder = UPLOAD_FOLDERS.get(upload_type, UPLOAD_FOLDERS['rooms'])
    filepath = os.path.join(upload_folder, filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def get_file_url(filename, upload_type='rooms'):
    """Get the URL for an uploaded file."""
    return f"/static/uploads/{upload_type}/{filename}"
