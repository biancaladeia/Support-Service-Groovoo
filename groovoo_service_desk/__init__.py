"""
Python package marker for the Groovoo service desk application.

Importing this package initialises the Flask application and exposes
``app`` for use with WSGI servers.
"""

from .app import app as app  # noqa: F401

