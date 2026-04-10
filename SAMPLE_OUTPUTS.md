# HMS Finale - Sample API Outputs

## Sample Data Structures

### Hotel Response
```json
{
  "id": 1,
  "name": "Ferlsafer Finale Hotel",
  "display_name": "Ferlsafer Finale",
  "location": "Dar es Salaam, Tanzania",
  "address": "Kigamboni, Dar es Salaam",
  "city": "Dar es Salaam",
  "postal_code": "00000",
  "country": "Tanzania",
  "phone": "+255 123 456 789",
  "email": "info@ferlsafer.com",
  "currency": "TZS",
  "timezone": "Africa/Dar_es_Salaam",
  "check_in_time": "14:00",
  "check_out_time": "11:00",
  "cancellation_policy": "Free cancellation up to 7 days before check-in",
  "children_policy": "Children under 12 stay free",
  "pet_policy": "Pets not allowed",
  "payment_policy": "Payment on arrival"
}
```

### Room Type Response
```json
{
  "id": 1,
  "name": "Deluxe Suite",
  "description": "Spacious suite with ocean view",
  "short_description": "Luxury suite with balcony",
  "category": "deluxe",
  "base_price": 150000.00,
  "price_usd": 395.00,
  "capacity": 2,
  "size_sqm": "45m²",
  "bed_type": "King Bed",
  "amenities": [
    "Air Conditioning",
    "Mini Bar",
    "Safe Deposit Box",
    "Coffee/Tea Maker",
    "Flat Screen TV",
    "Free WiFi",
    "Ocean View",
    "Balcony",
    "Bath Tub",
    "Hair Dryer"
  ],
  "primary_image": "room_type_1_abc12345.jpg",
  "images": [
    "room_type_1_abc12345.jpg",
    "room_type_1_def67890.jpg",
    "room_type_1_ghi11111.jpg"
  ],
  "available_rooms": 5,
  "tax_rate": 18.0,
  "is_active": true
}
```

### Room Response
```json
{
  "id": 101,
  "room_number": "301",
  "status": "Vacant",
  "floor": 3,
  "room_type": {
    "id": 1,
    "name": "Deluxe Suite",
    "base_price": 150000.00
  },
  "is_active": true,
  "description": "Corner suite with best ocean view"
}
```

### Guest Response
```json
{
  "id": 1001,
  "name": "John Smith",
  "phone": "+255 712 345 678",
  "email": "john.smith@email.com",
  "address": "123 Main St, City, Country",
  "id_type": "Passport",
  "id_number": "A12345678",
  "nationality": "Tanzanian",
  "created_at": "2024-03-15T10:30:00Z"
}
```

### Booking Response
```json
{
  "id": 5001,
  "booking_reference": "NGD-20240315-ABC123",
  "hotel_id": 1,
  "guest_id": 1001,
  "room_id": 101,
  "guest_name": "John Smith",
  "guest_email": "john.smith@email.com",
  "guest_phone": "+255 712 345 678",
  "room_type_requested": "Deluxe Suite",
  "check_in_date": "2024-04-01",
  "check_out_date": "2024-04-03",
  "status": "Reserved",
  "source": "website",
  "adults": 2,
  "children": 0,
  "total_amount": 300000.00,
  "amount_paid": 0.00,
  "balance": 300000.00,
  "special_requests": "Late check-in requested",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "created_at": "2024-03-15T10:30:00Z",
  "confirmed_at": "2024-03-15T10:35:00Z",
  "room": {
    "id": 101,
    "room_number": "301",
    "status": "Reserved"
  },
  "guest": {
    "id": 1001,
    "name": "John Smith",
    "email": "john.smith@email.com",
    "phone": "+255 712 345 678"
  }
}
```

### Invoice Response
```json
{
  "id": 2001,
  "hotel_id": 1,
  "booking_id": 5001,
  "invoice_number": "INV-NGD-20240315-ABC123",
  "total": 300000.00,
  "status": "Unpaid",
  "due_date": "2024-04-01",
  "created_at": "2024-03-15T10:30:00Z",
  "booking": {
    "id": 5001,
    "booking_reference": "NGD-20240315-ABC123",
    "guest_name": "John Smith"
  }
}
```

### Payment Response
```json
{
  "id": 3001,
  "hotel_id": 1,
  "booking_id": 5001,
  "invoice_id": 2001,
  "amount": 150000.00,
  "payment_method": "Cash",
  "payment_type": "partial",
  "transaction_id": "PAY-20240315-XYZ789",
  "status": "completed",
  "notes": "Partial payment on arrival",
  "created_at": "2024-04-01T15:00:00Z"
}
```

## API Endpoint Examples

### GET / (Home Page - Room Listings)
```json
{
  "room_types": [
    {
      "id": 1,
      "name": "Deluxe Suite",
      "description": "Spacious suite with ocean view",
      "short_description": "Luxury suite with balcony",
      "category": "deluxe",
      "base_price": 150000.00,
      "price_usd": 395.00,
      "capacity": 2,
      "size_sqm": "45m²",
      "bed_type": "King Bed",
      "amenities": ["Air Conditioning", "Mini Bar", "Safe Deposit Box"],
      "primary_image": "room_type_1_abc12345.jpg",
      "images": ["room_type_1_abc12345.jpg", "room_type_1_def67890.jpg"],
      "available_rooms": 5,
      "display_price": 395.00,
      "currency_symbol": "$"
    },
    {
      "id": 2,
      "name": "Standard Room",
      "description": "Comfortable room with city view",
      "short_description": "Cozy room for budget travelers",
      "category": "standard",
      "base_price": 80000.00,
      "price_usd": 210.00,
      "capacity": 2,
      "size_sqm": "25m²",
      "bed_type": "Double Bed",
      "amenities": ["Air Conditioning", "Free WiFi", "Flat Screen TV"],
      "primary_image": "room_type_2_jkl22222.jpg",
      "images": ["room_type_2_jkl22222.jpg"],
      "available_rooms": 12,
      "display_price": 210.00,
      "currency_symbol": "$"
    }
  ],
  "categories": ["deluxe", "standard", "superior"],
  "currency": "USD",
  "currency_symbol": "$"
}
```

### GET /room/1 (Room Detail)
```json
{
  "room": {
    "id": 1,
    "name": "Deluxe Suite",
    "description": "Spacious suite with ocean view, perfect for honeymooners and business travelers. Features a separate living area and premium amenities.",
    "short_description": "Luxury suite with balcony",
    "category": "deluxe",
    "base_price": 150000.00,
    "price_usd": 395.00,
    "capacity": 2,
    "size_sqm": "45m²",
    "bed_type": "King Bed",
    "amenities": [
      "Air Conditioning",
      "Mini Bar",
      "Safe Deposit Box",
      "Coffee/Tea Maker",
      "Flat Screen TV",
      "Free WiFi",
      "Ocean View",
      "Balcony",
      "Bath Tub",
      "Hair Dryer"
    ],
    "images": [
      "room_type_1_abc12345.jpg",
      "room_type_1_def67890.jpg",
      "room_type_1_ghi11111.jpg"
    ],
    "primary_image": "room_type_1_abc12345.jpg",
    "display_price": 395.00,
    "currency_symbol": "$"
  },
  "similar_rooms": [
    {
      "id": 3,
      "name": "Executive Suite",
      "category": "deluxe",
      "base_price": 180000.00,
      "display_price": 474.00,
      "currency_symbol": "$",
      "primary_image": "room_type_3_mno33333.jpg"
    }
  ]
}
```

### GET /check-availability?room_type_id=1&check_in=2024-04-01&check_out=2024-04-03
```json
{
  "success": true,
  "available": true,
  "message": "Rooms available for selected dates"
}
```

### GET /check-availability?room_type_id=1&check_in=2024-04-01&check_out=2024-04-02
```json
{
  "success": false,
  "available": false,
  "message": "No rooms available for selected dates"
}
```

### POST /book (Create Booking)
**Request:**
```json
{
  "guest_name": "Jane Doe",
  "guest_email": "jane.doe@email.com",
  "guest_phone": "+255 712 987 654",
  "room_type_id": 1,
  "check_in": "2024-04-01",
  "check_out": "2024-04-03",
  "adults": 2,
  "children": 0,
  "special_requests": "Early check-in if possible"
}
```

**Response (Success):**
```json
{
  "success": true,
  "booking_id": 5002,
  "booking_reference": "NGD-20240315-DEF456",
  "message": "Booking created successfully! Your booking reference is: NGD-20240315-DEF456"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Sorry, no Deluxe Suite rooms available for selected dates. Please try different dates or select another room type."
}
```

### POST /process-payment/5001 (Process Payment)
**Request:**
```json
{
  "amount": 150000.00,
  "payment_method": "Cash",
  "notes": "Partial payment on arrival"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Payment of 150000.00 processed successfully!",
  "payment_id": 3002
}
```

## Dashboard Statistics (Internal API)

### GET /hms/ (Dashboard Stats)
```json
{
  "stats": {
    "total_rooms": 50,
    "occupied_rooms": 35,
    "available_rooms": 10,
    "dirty_rooms": 3,
    "maintenance_rooms": 2,
    "revenue_today": 2500000.00,
    "revenue_yesterday": 1800000.00,
    "revenue_mtd": 45000000.00,
    "total_bookings": 125,
    "check_ins_today": 8,
    "check_outs_today": 5,
    "occupancy_rate": 70.0,
    "pending_housekeeping": 12,
    "low_stock_count": 5
  },
  "recent_bookings": [
    {
      "id": 5001,
      "booking_reference": "NGD-20240315-ABC123",
      "guest_name": "John Smith",
      "room_type_requested": "Deluxe Suite",
      "status": "Reserved",
      "check_in_date": "2024-04-01",
      "check_out_date": "2024-04-03"
    }
  ],
  "todays_arrivals": [
    {
      "id": 5002,
      "booking_reference": "NGD-20240314-XYZ789",
      "guest_name": "Jane Doe",
      "room_type_requested": "Standard Room",
      "status": "Confirmed",
      "check_in_date": "2024-03-15"
    }
  ],
  "todays_departures": [
    {
      "id": 5000,
      "booking_reference": "NGD-20240312-LMN456",
      "guest_name": "Bob Johnson",
      "room_type_requested": "Deluxe Suite",
      "status": "CheckedIn",
      "check_out_date": "2024-03-15"
    }
  ]
}
```

## Error Response Format

### Standard Error Response
```json
{
  "success": false,
  "error": "Error message description",
  "code": "ERROR_CODE"
}
```

### Validation Error Response
```json
{
  "success": false,
  "error": "Validation failed",
  "errors": {
    "guest_email": "Please enter a valid email address",
    "check_in": "Check-in date is required",
    "room_type_id": "Please select a room type"
  }
}
```

### Authentication Error Response
```json
{
  "success": false,
  "error": "Authentication required",
  "code": "AUTH_REQUIRED"
}
```

## Currency Conversion Examples

### TZS Prices
```json
{
  "base_price": 150000.00,
  "currency": "TZS",
  "currency_symbol": "TSh",
  "display_price": "TSh 150,000"
}
```

### USD Prices (Converted)
```json
{
  "base_price": 150000.00,
  "currency": "USD",
  "currency_symbol": "$",
  "display_price": "$395.00"
}
```

## Room Status Flow Examples

### Booking Lifecycle
1. **Room Available** → **Guest Books** → **Room Status: Reserved**
2. **Guest Arrives** → **Check-in** → **Room Status: Occupied**
3. **Guest Departs** → **Check-out** → **Room Status: Dirty**
4. **Cleaning Complete** → **Room Status: Vacant** (Available for booking)

### Status Change Response
```json
{
  "success": true,
  "message": "Room 301 status changed from Vacant to Reserved",
  "room_id": 301,
  "old_status": "Vacant",
  "new_status": "Reserved",
  "changed_by": 101,
  "changed_at": "2024-03-15T10:30:00Z"
}
```

## Notification Examples

### New Booking Notification
```json
{
  "id": 1001,
  "user_id": 101,
  "hotel_id": 1,
  "type": "website",
  "title": "New booking: NGD-20240315-ABC123",
  "message": "John Smith (+255 712 345 678 | john.smith@email.com) booked Deluxe Suite — 01 Apr to 03 Apr 2024 (2 nights).",
  "link": "/hms/bookings/5001",
  "icon": "calendar",
  "color": "green",
  "is_read": false,
  "created_at": "2024-03-15T10:30:00Z"
}
```

### Payment Notification
```json
{
  "id": 1002,
  "user_id": 101,
  "hotel_id": 1,
  "type": "payment",
  "title": "Payment received: NGD-20240315-ABC123",
  "message": "Payment of TZS 150,000 received for booking NGD-20240315-ABC123 (Cash method).",
  "link": "/hms/bookings/5001",
  "icon": "credit-card",
  "color": "blue",
  "is_read": false,
  "created_at": "2024-04-01T15:00:00Z"
}
```
