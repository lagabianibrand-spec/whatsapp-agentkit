# agent/tools.py — Herramientas del agente LAGABIANI
# Generado por AgentKit

"""
Herramientas específicas del negocio LAGABIANI.
Incluye funciones para FAQ, toma de pedidos, calificación de leads,
agendamiento de visitas ART y soporte post-venta.
"""

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "Lunes a Sábado 10am–6pm EST"),
        "esta_abierto": _esta_en_horario(),
    }


def _esta_en_horario() -> bool:
    """Verifica si actualmente está dentro del horario de atención (EST)."""
    from datetime import timezone, timedelta
    est = timezone(timedelta(hours=-5))
    ahora = datetime.now(est)
    # Lunes=0, Domingo=6. LAGABIANI atiende Lun–Sab (0–5)
    if ahora.weekday() >= 6:  # Domingo
        return False
    return 10 <= ahora.hour < 18


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:800]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


# ════════════════════════════════════════════════════════════
# HERRAMIENTAS PARA LAGABIANI GIFT
# ════════════════════════════════════════════════════════════

CATALOGO_GIFT = [
    {"nombre": "Elena Petite",            "rosas": "~8",    "precio": 115},
    {"nombre": "Petite Round Box",        "rosas": "~7",    "precio": 149},
    {"nombre": "Round Box",               "rosas": "9–11",  "precio": 185},
    {"nombre": "Square Box",              "rosas": "—",     "precio": 199},
    {"nombre": "Heart Box",               "rosas": "~19",   "precio": 235},
    {"nombre": "Elena",                   "rosas": "~40",   "precio": 589},
    {"nombre": "Rectangular Box",         "rosas": "~115",  "precio": 895},
    {"nombre": "I Love You Letter Box",   "rosas": "~115",  "precio": 1195},
    {"nombre": "Grand Rectangular Box",   "rosas": "~135",  "precio": 1295},
    {"nombre": "Grand Round Box",         "rosas": "~170",  "precio": 1895},
]


def obtener_catalogo_gift() -> list[dict]:
    """Retorna el catálogo completo de productos LAGABIANI GIFT."""
    return CATALOGO_GIFT


def sugerir_producto_gift(presupuesto_max: float = None, ocasion: str = "") -> list[dict]:
    """
    Sugiere productos GIFT según presupuesto y ocasión.

    Args:
        presupuesto_max: Presupuesto máximo del cliente en USD
        ocasion: Descripción de la ocasión (cumpleaños, aniversario, etc.)

    Returns:
        Lista de productos sugeridos
    """
    catalogo = CATALOGO_GIFT

    if presupuesto_max:
        catalogo = [p for p in catalogo if p["precio"] <= presupuesto_max]

    # Sugerir hasta 3 opciones en el rango de presupuesto
    return catalogo[:3] if len(catalogo) > 3 else catalogo


def registrar_interes_pedido(telefono: str, producto: str, color_flores: str = "",
                              color_caja: str = "", mensaje_tarjeta: str = "",
                              direccion_envio: str = "") -> dict:
    """
    Registra el interés de un cliente en hacer un pedido GIFT.
    Retorna un resumen para confirmar con el cliente antes de proceder.

    Args:
        telefono: Número del cliente
        producto: Nombre del producto elegido
        color_flores: Color de flores solicitado
        color_caja: Color de caja solicitado
        mensaje_tarjeta: Mensaje para la tarjeta personalizada
        direccion_envio: Dirección de envío

    Returns:
        Diccionario con el resumen del pedido
    """
    pedido = {
        "telefono": telefono,
        "producto": producto,
        "color_flores": color_flores or "Por definir",
        "color_caja": color_caja or "Por definir",
        "mensaje_tarjeta": mensaje_tarjeta or "Sin mensaje",
        "direccion_envio": direccion_envio or "Por definir",
        "estado": "pendiente_confirmacion",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info(f"Nuevo interés de pedido GIFT — {telefono}: {producto}")
    return pedido


# ════════════════════════════════════════════════════════════
# HERRAMIENTAS PARA LAGABIANI ART
# ════════════════════════════════════════════════════════════

def registrar_consulta_art(telefono: str, tipo_espacio: str = "",
                            ubicacion: str = "", estilo_colores: str = "",
                            tiene_fotos: bool = False) -> dict:
    """
    Registra la información de un proyecto ART antes de escalar al equipo.

    Args:
        telefono: Número del cliente
        tipo_espacio: Hotel, restaurante, residencia, etc.
        ubicacion: Ciudad o zona en Florida
        estilo_colores: Preferencias de estilo y colores
        tiene_fotos: Si el cliente indicó que puede enviar fotos

    Returns:
        Diccionario con el resumen de la consulta ART
    """
    consulta = {
        "telefono": telefono,
        "tipo_espacio": tipo_espacio or "Por confirmar",
        "ubicacion": ubicacion or "Por confirmar",
        "estilo_colores": estilo_colores or "Por confirmar",
        "fotos_disponibles": tiene_fotos,
        "estado": "pendiente_equipo_art",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info(f"Nueva consulta ART — {telefono}: {tipo_espacio} en {ubicacion}")
    return consulta


# ════════════════════════════════════════════════════════════
# HERRAMIENTAS DE SOPORTE POST-VENTA
# (Casos de devolución/cambio → escalar a humano siempre)
# ════════════════════════════════════════════════════════════

def requiere_escalamiento_humano(motivo: str) -> dict:
    """
    Indica que el caso debe ser manejado por un humano del equipo LAGABIANI.
    Retorna el mensaje estándar de escalamiento.

    Args:
        motivo: Razón del escalamiento (devolución, reclamo, etc.)

    Returns:
        Diccionario con instrucciones de escalamiento
    """
    logger.info(f"Escalamiento a humano solicitado — motivo: {motivo}")
    return {
        "escalar": True,
        "motivo": motivo,
        "mensaje_cliente": (
            "Para ayudarte mejor con esto, voy a conectarte con alguien de nuestro equipo. "
            "Un momento, por favor. También puedes escribirnos directamente al +1 (954) 347-6492."
        ),
        "contacto": "+1 (954) 347-6492",
    }
