"""
Extensiones centralizadas de Flask.

Todas las extensiones (db, login, oauth) se inicializan aquí
y se configuran en create_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

# SQLAlchemy
db = SQLAlchemy()

# Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'autenticacion.login'
login_manager.login_message = None
login_manager.login_message_category = None

# OAuth
oauth = OAuth()
