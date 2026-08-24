from app.extensions import db
from datetime import datetime


class Obligacion(db.Model):
    __tablename__ = 'obligacion'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    reportes = db.relationship('ReporteMensual', backref='obligacion', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Obligacion {self.numero}>'
