"""WSGI entry point for Gunicorn."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.config import ProductionConfig

app = create_app(ProductionConfig)
