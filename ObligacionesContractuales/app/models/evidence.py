from app.extensions import db
from datetime import datetime


class Evidencia(db.Model):
    __tablename__ = 'evidencia'
    id = db.Column(db.Integer, primary_key=True)
    numero_actividad = db.Column(db.Integer, nullable=False)
    imagen_path = db.Column(db.String(500), nullable=False)
    anuncio_usuario = db.Column(db.Text, nullable=False)
    descripcion_visual_ia = db.Column(db.Text, nullable=True)
    descripcion_actividad = db.Column(db.Text, nullable=False)
    fecha_actividad = db.Column(db.Date, nullable=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reporte_mensual.id'), nullable=False)
    fecha_carga = db.Column(db.DateTime, default=datetime.utcnow)

    def _extraer_contenido_funcional(self, anuncio, visual):
        from vision_analyzer import _limpiar_texto
        texto = anuncio
        if visual and visual.lower() not in anuncio.lower():
            visual_limpio = _limpiar_texto(visual)
            if visual_limpio:
                texto = f"{anuncio}. {visual_limpio}"
        return _limpiar_texto(texto)

    def generar_descripcion_automatica(self, obligacion):
        anuncio = self.anuncio_usuario.strip()
        visual = (self.descripcion_visual_ia or "").strip()
        contenido = self._extraer_contenido_funcional(anuncio, visual)

        templates = [
            "Durante el periodo reportado se adelanto {contenido} Esta accion contribuye al cumplimiento de la obligacion contractual y fortalece el avance del objeto del contrato.",
            "Se ejecuto {contenido} como parte de las actividades programadas para el mes. El desarrollo de esta tarea responde a los compromisos establecidos en el contrato y aporta al logro de los resultados esperados.",
            "Como parte del plan de trabajo contractual, se realizo {contenido} Esta labor se desarrollo conforme a lo planeado y dentro de los terminos pactados, garantizando la continuidad operativa del proyecto.",
            "En el marco de la obligacion contractual, se llevo a cabo {contenido} La actividad fue desarrollada de manera oportuna y contribuye al seguimiento de los indicadores de gestion definidos.",
            "Se efectuo {contenido} durante el periodo de reporte. Esta accion representa un avance significativo en el cumplimiento de los compromisos contractuales y aporta al cumplimiento de las metas establecidas.",
            "Dentro del plan operativo del contrato, se desarrollo {contenido} La ejecucion de esta actividad se realizo en cumplimiento de las obligaciones pactadas y aporta al cumplimiento de los objetivos del proyecto.",
            "Se adelanto {contenido} como parte del seguimiento a las actividades contractuales. El resultado de esta labor se consolida dentro del marco de los entregables definidos y contribuye al cumplimiento mensual.",
            "En cumplimiento de la obligacion contractual, se realizo {contenido} Esta actividad fue ejecutada durante el periodo reportado y se encuentra alineada con los objetivos y alcance definidos en el contrato.",
            "Se gestiono y ejecuto {contenido} durante el mes reportado. Esta labor forma parte de las acciones contractuales planificadas y contribuye al cumplimiento de los entregables pactados.",
            "Como parte del desarrollo de las actividades contractuales, se adelanto {contenido} Esta accion se ejecuto conforme a la programacion establecida y aporta al seguimiento de los compromisos del contrato.",
        ]

        idx = zlib.crc32(contenido.encode('utf-8')) % len(templates)
        return templates[idx].format(contenido=contenido)

    def __repr__(self):
        return f'<Evidencia {self.numero_actividad}>'
