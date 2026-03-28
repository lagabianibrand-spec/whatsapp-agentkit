# agent/providers/whapi.py — Adaptador para Whapi.cloud
# Generado por AgentKit para LAGABIANI

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorWhapi(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Whapi.cloud (REST API simple)."""

    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.url_envio = "https://gate.whapi.cloud/messages/text"

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload de Whapi.cloud."""
        body = await request.json()
        logger.info(f"Webhook Whapi payload completo: {body}")

        raw_messages = body.get("messages", [])
        if not raw_messages:
            logger.info(f"Webhook sin mensajes — evento de sistema o vacío. Keys: {list(body.keys())}")
            return []

        mensajes = []
        for msg in raw_messages:
            chat_id = msg.get("chat_id", "")
            tipo = msg.get("type", "")
            from_me = msg.get("from_me", False)
            logger.info(f"Evento — chat_id: {chat_id}, tipo: {tipo}, from_me: {from_me}")

            # Ignorar mensajes salientes o enviados por la API
            source = msg.get("source", "")
            if from_me or source == "api":
                logger.info(f"Ignorando — from_me: {from_me}, source: {source}")
                continue

            # Solo procesar mensajes de texto
            if tipo != "text":
                logger.info(f"Ignorando mensaje tipo '{tipo}' — solo proceso texto")
                continue

            texto = msg.get("text", {}).get("body", "").strip()
            if not texto:
                logger.info("Mensaje tipo text sin cuerpo — ignorando")
                continue

            # chat_id debe ser válido (contener @)
            if not chat_id or "@" not in chat_id:
                logger.warning(f"chat_id inválido: '{chat_id}' — ignorando")
                continue

            logger.info(f"Mensaje REAL aceptado — chat_id: {chat_id}, texto: {texto}")
            mensajes.append(MensajeEntrante(
                telefono=chat_id,
                texto=texto,
                mensaje_id=msg.get("id", ""),
                es_propio=False,
            ))
        return mensajes

    async def parsear_webhook_from_body(self, body: dict) -> list[MensajeEntrante]:
        """Versión que recibe el body ya parseado (evita leer el request dos veces)."""
        logger.info(f"Webhook Whapi payload: {body}")
        raw_messages = body.get("messages", [])
        if not raw_messages:
            logger.info(f"Sin mensajes — keys: {list(body.keys())}")
            return []

        mensajes = []
        for msg in raw_messages:
            chat_id = msg.get("chat_id", "")
            tipo = msg.get("type", "")
            from_me = msg.get("from_me", False)
            source = msg.get("source", "")
            logger.info(f"Evento — chat_id: {chat_id}, tipo: {tipo}, from_me: {from_me}")

            if from_me or source == "api":
                logger.info(f"Ignorando — from_me: {from_me}, source: {source}")
                continue
            if tipo != "text":
                logger.info(f"Ignorando tipo '{tipo}'")
                continue
            texto = msg.get("text", {}).get("body", "").strip()
            if not texto:
                continue
            if not chat_id or "@" not in chat_id:
                logger.warning(f"chat_id inválido: '{chat_id}'")
                continue

            logger.info(f"Mensaje REAL aceptado — chat_id: {chat_id}, texto: {texto}")
            mensajes.append(MensajeEntrante(
                telefono=chat_id,
                texto=texto,
                mensaje_id=msg.get("id", ""),
                es_propio=False,
            ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Whapi.cloud. El campo 'to' acepta chat_id completo."""
        if not self.token:
            logger.warning("WHAPI_TOKEN no configurado — mensaje no enviado")
            return False
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"to": telefono, "body": mensaje}
        logger.info(f"Enviando a Whapi — to: {telefono}, body: {mensaje[:50]}...")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.url_envio,
                json=payload,
                headers=headers,
            )
            logger.info(f"Respuesta Whapi: {r.status_code} — {r.text[:200]}")
            if r.status_code != 200:
                logger.error(f"Error Whapi: {r.status_code} — {r.text}")
            return r.status_code == 200
