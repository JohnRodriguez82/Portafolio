from app.extensions import db
from datetime import datetime


class ReporteMensual(db.Model):
    __tablename__ = 'reporte_mensual'
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    fecha_inicio_reporte = db.Column(db.Date, nullable=False)
    fecha_fin_reporte = db.Column(db.Date, nullable=False)
    cerrado = db.Column(db.Boolean, default=False, nullable=False)
    obligacion_id = db.Column(db.Integer, db.ForeignKey('obligacion.id'), nullable=False)
    evidencias = db.relationship('Evidencia', backref='reporte', lazy=True, cascade='all, delete-orphan')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nombre_mes(self):
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[self.mes]

    def __repr__(self):
        return f'<ReporteMensual {self.mes}-{self.anio}>'
