# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para LAGABIANI

"""
Servidor principal del agente de WhatsApp.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

import httpx
from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp — se instancia DESPUÉS de load_dotenv() para que el token esté disponible
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — LAGABIANI WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)


async def enviar_mensaje_instagram(sender_id: str, respuesta: str) -> bool:
    """Envía respuesta a Instagram via Meta Messenger Send API."""
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    if not token:
        logger.warning("META_PAGE_ACCESS_TOKEN no configurado")
        return False
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta},
        "messaging_type": "RESPONSE"
    }
    # DEBUG — log completo del request y response para diagnóstico
    logger.info(f"[IG-SEND] URL: {url}")
    logger.info(f"[IG-SEND] RECIPIENT ID: {sender_id}")
    logger.info(f"[IG-SEND] PAYLOAD: {payload}")
    logger.info(f"[IG-SEND] TOKEN presente: {'SÍ' if token else 'NO'} — primeros 10 chars: {token[:10]}...")
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, params={"access_token": token})
        logger.info(f"[IG-SEND] STATUS: {r.status_code}")
        logger.info(f"[IG-SEND] RESPONSE BODY COMPLETO: {r.text}")
        if r.status_code != 200:
            logger.error(f"[IG-SEND] ERROR — {r.status_code}: {r.text}")
        return r.status_code == 200


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "agentkit-lagabiani"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook — soporta Meta Messenger/Instagram y Whapi."""
    params = request.query_params

    # Verificación de Meta (hub.mode + hub.verify_token + hub.challenge)
    if "hub.mode" in params:
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token", "")
        challenge = params.get("hub.challenge", "")
        expected_token = os.getenv("META_VERIFY_TOKEN", "")

        if mode == "subscribe" and token == expected_token:
            logger.info("Meta webhook verificado correctamente")
            return PlainTextResponse(challenge, status_code=200)
        else:
            logger.warning(f"Meta webhook: token inválido — recibido: {token}")
            raise HTTPException(status_code=403, detail="Verify token inválido")

    # Fallback para otros proveedores (Whapi no usa GET de verificación)
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Recibe mensajes de WhatsApp (Whapi) e Instagram (Meta). Los procesa y responde."""
    try:
        body = await request.json()

        # ── Meta / Instagram ──────────────────────────────────────
        if body.get("object") in ("instagram", "page"):
            for entry in body.get("entry", []):
                for event in entry.get("messaging", []):
                    sender_id = event.get("sender", {}).get("id", "")
                    mensaje_data = event.get("message", {})
                    texto = mensaje_data.get("text", "").strip()

                    if not texto or mensaje_data.get("is_echo"):
                        continue

                    logger.info(f"Instagram — sender: {sender_id}, texto: {texto}")
                    historial = await obtener_historial(sender_id)
                    respuesta = await generar_respuesta(texto, historial)
                    await guardar_mensaje(sender_id, "user", texto)
                    await guardar_mensaje(sender_id, "assistant", respuesta)
                    await enviar_mensaje_instagram(sender_id, respuesta)
                    logger.info(f"Instagram respuesta a {sender_id}: {respuesta}")
            return {"status": "ok"}

        # ── WhatsApp / Whapi ──────────────────────────────────────
        mensajes = await proveedor.parsear_webhook_from_body(body)
        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue
            logger.info(f"WhatsApp — {msg.telefono}: {msg.texto}")
            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)
            await proveedor.enviar_mensaje(msg.telefono, respuesta)
            logger.info(f"WhatsApp respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
