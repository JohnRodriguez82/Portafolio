from app.extensions import db
from datetime import datetime


class Contrato(db.Model):
    __tablename__ = 'contrato'
    id = db.Column(db.Integer, primary_key=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    contratista = db.Column(db.String(200), nullable=True)
    numero_contrato = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    etapa = db.Column(db.String(50), default='Reporte en Proceso')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    obligaciones = db.relationship('Obligacion', backref='contrato', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Contrato {self.numero_contrato}>'
