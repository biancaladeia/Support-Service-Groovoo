"""
Configuration for the Groovoo service desk application.

Values defined here configure the Flask application, database and
upload handling.  Adjust the ``SECRET_KEY`` to a random string before
deploying to production.  The database is stored relative to this file.
"""

import os

# Base directory of this package
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Secret key used by Flask to secure sessions and forms
SECRET_KEY = 'please-change-me'  # Replace with a random string in production

# SQLite database location
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'service_desk.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Where uploaded files are stored (relative to package directory)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

# Allowed file extensions for attachments
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}