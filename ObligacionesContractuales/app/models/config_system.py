from app.extensions import db
from datetime import datetime


class ConfiguracionSistema(db.Model):
    __tablename__ = 'configuracion_sistema'
    id = db.Column(db.Integer, primary_key=True)
    gemini_api_key_encriptada = db.Column(db.Text, nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ConfiguracionSistema {self.id}>'
