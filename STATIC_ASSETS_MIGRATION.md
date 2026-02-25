# Static Assets Migration Plan

## Overview
Consolidate all room images from both the website and HMS into a single source of truth.

## Directory Structure

```
hotel_pms/
├── app/
│   ├── static/
│   │   └── uploads/
│   │       ├── rooms/          # Room type images (shared)
│   │       ├── gallery/        # General hotel gallery
│   │       ├── logos/          # Hotel logos and branding
│   │       └── documents/      # PDFs, invoices, etc.
│   └── models.py               # Unified models with image_filename fields
```

## Migration Steps

### Step 1: Create Directory Structure
```bash
mkdir -p app/static/uploads/rooms
mkdir -p app/static/uploads/gallery
mkdir -p app/static/uploads/logos
mkdir -p app/static/uploads/documents
```

### Step 2: Copy Website Room Images
Source: `ngenda-hotel-website/static/images/rooms/`
Destination: `app/static/uploads/rooms/`

Files to migrate:
- room3.jpg, room4.jpg, room4.JPG, room5.jpg, room5.JPG, room6.jpg, room6.JPG
- roomview.jpg, roomview1.jpg through roomview6.jpg
- about2.jpg

### Step 3: Update RoomImage Model
The `RoomImage` model now uses `image_filename` instead of full URL:

```python
class RoomImage(db.Model):
    __tablename__ = "room_images"
    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)  # Just filename
    is_primary = db.Column(db.Boolean, default=False)
    
    @property
    def url(self):
        return f"/static/uploads/rooms/{self.image_filename}"
```

### Step 4: Update RoomType Model
Added fields for website compatibility:
- `price_usd` - USD equivalent for international guests
- `category` - For filtering (classic, superior, deluxe, executive)
- `amenities` - JSON array of amenities

### Step 5: Image Upload Handler
Create a utility for handling uploads:

```python
# app/utils/uploads.py
import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = 'app/static/uploads/rooms'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_room_image(file, room_type_id=None):
    """Save room image and return filename."""
    if not allowed_file(file.filename):
        return None
    
    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"room_{uuid.uuid4().hex[:12]}.{ext}"
    
    # Save to uploads folder
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    return filename
```

## Website Template Updates

### Update image references in templates:
```html
<!-- Before -->
<img src="{{ url_for('static', filename='images/rooms/room3.jpg') }}">

<!-- After -->
<img src="{{ url_for('static', filename='uploads/rooms/' + room.image_filename) }}">
```

## API Response Format

### GET /api/public/rooms
```json
{
  "success": true,
  "rooms": [
    {
      "id": 1,
      "name": "Classic Balcony Room",
      "category": "classic",
      "price": 299000,
      "price_usd": 115,
      "image": "/static/uploads/rooms/room_classic_001.jpg",
      "images": [
        "/static/uploads/rooms/room_classic_001.jpg",
        "/static/uploads/rooms/room_classic_002.jpg"
      ],
      "amenities": ["AC", "WiFi", "Balcony", "Mini Bar"],
      "description": "Full description...",
      "short_description": "Brief description",
      "capacity": 3,
      "size_sqm": "30m²",
      "bed_type": "Double Bed"
    }
  ]
}
```

## Rollback Plan
If migration fails:
1. Keep original `ngenda-hotel-website/static/images/` folder intact
2. Revert `RoomImage.url` property to use old path
3. Update templates to reference old paths

## Post-Migration Checklist
- [ ] All room images copied to `app/static/uploads/rooms/`
- [ ] Database `room_images` table updated with filenames
- [ ] Website templates updated to use new paths
- [ ] API endpoints return correct image URLs
- [ ] Image upload functionality tested
- [ ] Old image folder archived (not deleted)
