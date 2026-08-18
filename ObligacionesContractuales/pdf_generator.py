"""
Generador de PDF para Reportes de Cumplimiento de Obligaciones Contractuales
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os
from datetime import datetime


class PDFGenerator:
    def __init__(self, output_path):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='TitleCustom',
            fontName='Helvetica-Bold',
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a1a')
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#2c3e50')
        ))
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            fontName='Helvetica',
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=14
        ))
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.white
        ))
        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontName='Helvetica',
            fontSize=9,
            alignment=TA_LEFT,
            leading=12
        ))
        self.styles.add(ParagraphStyle(
            name='ActivityDesc',
            fontName='Helvetica',
            fontSize=9,
            alignment=TA_JUSTIFY,
            leading=13,
            spaceAfter=4
        ))

    def generar_reporte(self, reporte, obligacion, evidencias, contrato):
        """
        Genera el PDF del reporte mensual de una obligación.
        Tabla: # | Actividad realizada | Fecha | Evidencia (solo imagen)
        """
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        story = []

        # Título principal
        story.append(Paragraph(
            "PLANTILLA DE REPORTE DE CUMPLIMIENTO DE OBLIGACIÓN CONTRACTUAL",
            self.styles['TitleCustom']
        ))
        story.append(Spacer(1, 0.2*inch))

        # Tabla de metadatos (Contratista, N° Contrato, Mes y Obligación No.)
        mes_nombre = reporte.nombre_mes
        meta_data = [
            [Paragraph("<b>Contratista</b>", self.styles['TableCell']),
             Paragraph(contrato.contratista or "No especificado", self.styles['TableCell'])],
            [Paragraph("<b>Número de contrato</b>", self.styles['TableCell']),
             Paragraph(contrato.numero_contrato or "No especificado", self.styles['TableCell'])],
            [Paragraph("<b>Mes reportado</b>", self.styles['TableCell']),
             Paragraph(mes_nombre, self.styles['TableCell'])],
            [Paragraph("<b>Obligación No.</b>", self.styles['TableCell']),
             Paragraph(str(obligacion.numero), self.styles['TableCell'])]
        ]
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.2*inch))

        # Descripción de la obligación
        story.append(Paragraph("Descripción de la obligación", self.styles['SectionHeader']))
        story.append(Paragraph(obligacion.descripcion, self.styles['BodyTextCustom']))
        story.append(Spacer(1, 0.15*inch))

        # Actividades y evidencias
        story.append(Paragraph("Actividades y evidencias", self.styles['SectionHeader']))

        # Construir filas de la tabla: # | Actividad | Fecha | Evidencia (solo imagen)
        table_data = [
            [Paragraph("#", self.styles['TableHeader']),
             Paragraph("Actividad realizada", self.styles['TableHeader']),
             Paragraph("Fecha", self.styles['TableHeader']),
             Paragraph("Evidencia", self.styles['TableHeader'])]
        ]

        if not evidencias:
            table_data.append([
                Paragraph("-", self.styles['TableCell']),
                Paragraph("No se han registrado actividades con evidencias para este período.", self.styles['TableCell']),
                Paragraph("-", self.styles['TableCell']),
                Paragraph("-", self.styles['TableCell'])
            ])
        else:
            for ev in evidencias:
                # Columna Evidencia: SOLO la imagen, sin repetir el texto
                evidencia_content = []
                if os.path.exists(ev.imagen_path):
                    try:
                        img = Image(ev.imagen_path, width=3*inch, height=1.7*inch)
                        img.hAlign = 'CENTER'
                        evidencia_content.append(img)
                    except Exception:
                        evidencia_content.append(Paragraph(f"[Imagen: {os.path.basename(ev.imagen_path)}]", self.styles['TableCell']))
                else:
                    evidencia_content.append(Paragraph(f"[Imagen: {os.path.basename(ev.imagen_path)}]", self.styles['TableCell']))

                # Fecha: usa fecha_actividad si existe, sino fecha_carga
                if ev.fecha_actividad:
                    fecha_str = ev.fecha_actividad.strftime("%d-%m-%Y")
                else:
                    fecha_str = ev.fecha_carga.strftime("%d-%m-%Y") if ev.fecha_carga else ""

                table_data.append([
                    Paragraph(str(ev.numero_actividad), self.styles['TableCell']),
                    Paragraph(ev.descripcion_actividad, self.styles['TableCell']),
                    Paragraph(fecha_str, self.styles['TableCell']),
                    evidencia_content
                ])

        # Crear tabla de actividades
        act_table = Table(table_data, colWidths=[0.4*inch, 2.2*inch, 0.9*inch, 2.9*inch])
        act_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(act_table)
        story.append(Spacer(1, 0.2*inch))

        # Pie de página con información del período
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            f"<i>Período del reporte: {reporte.fecha_inicio_reporte.strftime('%d-%m-%Y')} a {reporte.fecha_fin_reporte.strftime('%d-%m-%Y')}</i>",
            ParagraphStyle('Footer', fontName='Helvetica-Oblique', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))
        story.append(Paragraph(
            f"<i>Documento generado el {datetime.now().strftime('%d-%m-%Y %H:%M')}</i>",
            ParagraphStyle('Footer2', fontName='Helvetica-Oblique', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))

        doc.build(story)
        return self.output_path
