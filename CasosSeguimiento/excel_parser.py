"""
Procesa archivos Excel/CSV con campos parametrizables.
Actualización incremental: compara por número de caso y actualiza cambios.
"""
import pandas as pd
from datetime import datetime
from database import get_db, Caso, LogProcesamiento
from config_manager import get_campos_excel, get_tipo_archivo


def _parse_fecha(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"]:
        try:
            return datetime.strptime(str(valor).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _detectar_columnas(df_columns, campos_config):
    """Mapea columnas del archivo a campos configurados usando sinónimos."""
    df_columns_lower = {str(c).strip().lower(): c for c in df_columns}
    mapeo = {}
    no_detectados = []

    for campo in campos_config:
        campo_id = campo["id"]
        sinonimos = [s.strip().lower() for s in campo.get("sinonimos", "").split(",") if s.strip()]
        encontrado = None

        for sin in sinonimos:
            for col_lower, col_original in df_columns_lower.items():
                if sin in col_lower:
                    encontrado = col_original
                    break
            if encontrado:
                break

        if encontrado:
            mapeo[campo_id] = encontrado
        elif campo.get("obligatorio", False):
            no_detectados.append(campo["nombre"])

    return mapeo, no_detectados


def _leer_archivo(filepath: str):
    """Lee Excel o CSV según configuración y extensión."""
    tipo_cfg = get_tipo_archivo()
    ext = filepath.lower().split(".")[-1]

    if ext == "csv" or tipo_cfg == "csv":
        # Intentar con coma, punto y coma, o tab
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(filepath, sep=sep, engine="python")
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
        raise ValueError("No se pudo leer el CSV. Verifica el separador (coma, punto y coma o tab).")
    else:
        return pd.read_excel(filepath)


def procesar_archivo(filepath: str) -> dict:
    """
    Lee el archivo (Excel/CSV), detecta columnas según configuración,
    inserta nuevos casos o actualiza existentes comparando por número de caso.
    """
    db = get_db()
    try:
        df = _leer_archivo(filepath)
        if df.empty:
            return {"ok": False, "error": "El archivo está vacío."}

        campos_config = get_campos_excel()
        mapeo, faltantes = _detectar_columnas(df.columns.tolist(), campos_config)

        if faltantes:
            return {"ok": False, "error": f"Columnas obligatorias no detectadas: {faltantes}. Columnas encontradas: {list(df.columns)}"}

        insertados = 0
        actualizados = 0
        errores = []
        cambios_detectados = []

        # Mapeo de campos base que conocemos en el modelo
        campos_base = {"sede", "seccion", "estudios", "organo", "profesional", "estado"}
        campos_fecha = {"fecha_ingreso", "fecha_validacion"}

        for idx, row in df.iterrows():
            try:
                # Número de caso (obligatorio)
                if "numero_caso" not in mapeo:
                    errores.append(f"Fila {idx+2}: No se detectó columna de número de caso.")
                    continue

                num_caso = str(row[mapeo["numero_caso"]]).strip()
                if not num_caso or num_caso.lower() == "nan":
                    continue

                # Buscar si ya existe
                existe = db.query(Caso).filter(Caso.numero_caso == num_caso).first()

                # Extraer valores según configuración
                valores = {}
                for campo_id, col_name in mapeo.items():
                    val = row[col_name]
                    cfg_campo = next((c for c in campos_config if c["id"] == campo_id), None)

                    if cfg_campo and cfg_campo.get("tipo") == "fecha":
                        valores[campo_id] = _parse_fecha(val)
                    else:
                        valores[campo_id] = str(val).strip() if pd.notna(val) else ""

                fecha_ingreso = valores.get("fecha_ingreso")
                fecha_validacion = valores.get("fecha_validacion")
                profesional = valores.get("profesional", "Sin asignar")
                estado_raw = valores.get("estado", "").upper()

                # Determinar estado
                if estado_raw:
                    estado = estado_raw
                else:
                    estado = "RESUELTO" if fecha_validacion else "PENDIENTE"

                # Preparar campos extra (los que no son base)
                campos_extra = {}
                for campo_id, val in valores.items():
                    if campo_id not in campos_base and campo_id not in campos_fecha and campo_id != "numero_caso":
                        campos_extra[campo_id] = val

                if existe:
                    # Actualización incremental: detectar cambios
                    cambios = []

                    if existe.fecha_validacion != fecha_validacion:
                        cambios.append(f"Fecha validación: {existe.fecha_validacion} → {fecha_validacion}")
                        existe.fecha_validacion = fecha_validacion

                    if existe.estado != estado:
                        cambios.append(f"Estado: {existe.estado} → {estado}")
                        existe.estado = estado

                    if existe.profesional != profesional:
                        cambios.append(f"Profesional: {existe.profesional} → {profesional}")
                        existe.profesional = profesional

                    # Actualizar campos base opcionales
                    for base_field in campos_base:
                        if base_field in valores:
                            nuevo_val = valores[base_field]
                            actual = getattr(existe, base_field, None) or ""
                            if str(actual) != str(nuevo_val):
                                setattr(existe, base_field, nuevo_val)

                    # Actualizar campos extra
                    if campos_extra:
                        actual_extra = existe.campos_extra or {}
                        actual_extra.update(campos_extra)
                        existe.campos_extra = actual_extra

                    if cambios:
                        cambios_detectados.append(f"Caso {num_caso}: {', '.join(cambios)}")

                    actualizados += 1
                else:
                    nuevo = Caso(
                        numero_caso=num_caso,
                        fecha_ingreso=fecha_ingreso,
                        fecha_validacion=fecha_validacion,
                        estado=estado,
                        profesional=profesional,
                        sede=valores.get("sede", ""),
                        seccion=valores.get("seccion", ""),
                        estudios=valores.get("estudios", ""),
                        organo=valores.get("organo", ""),
                        campos_extra=campos_extra,
                    )
                    db.add(nuevo)
                    insertados += 1

            except Exception as e:
                errores.append(f"Fila {idx+2}: {str(e)}")

        db.commit()

        # Guardar log de procesamiento
        log = LogProcesamiento(
            archivo=filepath,
            insertados=insertados,
            actualizados=actualizados,
            errores=len(errores),
            detalle="\n".join(cambios_detectados[:20])  # Primeros 20 cambios
        )
        db.add(log)
        db.commit()

        return {
            "ok": True,
            "insertados": insertados,
            "actualizados": actualizados,
            "errores": errores,
            "cambios": cambios_detectados,
            "columnas_detectadas": mapeo,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()
