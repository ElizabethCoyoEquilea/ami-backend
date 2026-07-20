from app.models.solicitudes.solicitud import Solicitud


def _obtener_recomendacion_por_texto(texto: str) -> str | None:
    if not texto:
        return None
    
    texto_min = texto.lower()
    
    if "batería" in texto_min or "bateria" in texto_min:
        return "Posible batería descargada. Evite intentar múltiples arranques consecutivos para no descargarla completamente."
    if "llanta" in texto_min or "neumatico" in texto_min or "neumático" in texto_min:
        return "Se recomienda no continuar conduciendo. Solicite cambio de neumático o asistencia."
    if "aceite" in texto_min:
        return "Revise el nivel de aceite antes de continuar utilizando el vehículo."
    if "motor" in texto_min:
        return "Se recomienda apagar el motor y esperar asistencia técnica para evitar daños mayores."
    if "temperatura" in texto_min or "sobrecalentamiento" in texto_min or "radiador" in texto_min:
        return "El vehículo presenta posible sobrecalentamiento. No retire la tapa del radiador mientras el motor esté caliente."
    if "freno" in texto_min:
        return "No continúe conduciendo el vehículo hasta revisar el sistema de frenos."
    if "ruido" in texto_min or "sonido" in texto_min:
        return "Se detecta una posible falla mecánica. Evite utilizar el vehículo hasta realizar una inspección."
    
    return None


def _obtener_prioridad_por_texto(texto: str) -> str:
    if not texto:
        return "baja"
    
    texto_min = texto.lower()
    
    if "temperatura" in texto_min or "sobrecalentamiento" in texto_min or "radiador" in texto_min:
        return "urgente"
    if "freno" in texto_min:
        return "alta"
    if "motor" in texto_min:
        return "alta"
    if "batería" in texto_min or "bateria" in texto_min:
        return "media"
    if "llanta" in texto_min or "neumatico" in texto_min or "neumático" in texto_min:
        return "media"
    
    return "baja"


def generar_recomendacion(solicitud: Solicitud) -> str:
    # 1. Intentar con tipo de avería o categoría si están disponibles como atributos
    categoria = getattr(solicitud, "categoria", None) or getattr(solicitud, "tipo_averia", None)
    if categoria:
        rec_cat = _obtener_recomendacion_por_texto(str(categoria))
        if rec_cat:
            return rec_cat
            
    # 2. Respaldo: evaluar con la descripción de la solicitud
    desc = solicitud.descripcion or ""
    rec_desc = _obtener_recomendacion_por_texto(desc)
    if rec_desc:
        return rec_desc
        
    # 3. Caso por defecto si no coincide ninguna regla
    return "Se recomienda esperar la evaluación del proveedor para obtener un diagnóstico preciso."


def generar_prioridad(solicitud: Solicitud) -> str:
    # 1. Intentar con tipo de avería o categoría si están disponibles
    categoria = getattr(solicitud, "categoria", None) or getattr(solicitud, "tipo_averia", None)
    if categoria:
        pri_cat = _obtener_prioridad_por_texto(str(categoria))
        if pri_cat != "baja":
            return pri_cat
            
    # 2. Respaldo: evaluar con la descripción de la solicitud
    desc = solicitud.descripcion or ""
    return _obtener_prioridad_por_texto(desc)
