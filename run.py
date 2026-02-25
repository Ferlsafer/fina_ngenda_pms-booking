import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import Owner, Hotel, User, Room, RoomType, Booking, Guest, Invoice, Payment

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # In production, use gunicorn instead:
    # gunicorn -w 4 -b 0.0.0.0:8000 run:app
    
    print(f"Starting Flask app on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    
    app.run(host=host, port=port, debug=debug)
