"""Mock SMS/email notification generation, plus optional real email delivery.

SMS stays mock/log-only, by design (see PROJECT.md Out of Scope) -- no
Twilio/SNS integration. Email CAN be really sent via Gmail SMTP for demo
purposes, but only to a demo recipient (never a real vehicle owner lookup --
this system never attempts that), and the body always carries the
"SIMULADO" disclaimer so it never reads as a real official fine. Gmail
credentials are read from environment variables (see .env, gitignored) --
never hardcoded, never committed.
"""

import os
import random
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from synctrack import config  # noqa: F401  (loads .env into os.environ on import)

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
# Demo recipient defaults to the developer's own inbox -- this system never
# performs real plate-to-owner lookups, so there is no real owner address to
# send to; sending anywhere else would risk emailing an uninvolved stranger.
DEMO_NOTIFY_EMAIL = os.environ.get("DEMO_NOTIFY_EMAIL", "memitoscorado@gmail.com")

# Fake owner names -- this system has no real plate-to-owner registry access
# (that data sits with SAT/RENAP via the impuesto de circulacion, not with
# us). Names below are randomly assigned per plate purely to make the demo
# notification read naturally; they are NOT real people.
_FAKE_FIRST_NAMES = ["Carlos", "Maria", "Luis", "Ana", "Jose", "Andrea", "Miguel", "Sofia", "Pedro", "Gabriela"]
_FAKE_LAST_NAMES = ["Garcia", "Lopez", "Morales", "Hernandez", "Ramirez", "Gonzalez", "Perez", "Cruz", "Rodas", "Estrada"]


def fake_owner_name(plate):
    """Deterministic per-plate fake name (same plate -> same name within a run)."""
    rng = random.Random(plate)
    return f"{rng.choice(_FAKE_FIRST_NAMES)} {rng.choice(_FAKE_LAST_NAMES)}"


SMS_TEMPLATE = (
    "[SIMULADO] SyncTrack: Estimado/a {owner_name}, se detecto tu vehiculo placa {plate} "
    "circulando a {speed:.0f} km/h en una via con limite de {limit:.0f} km/h el {timestamp}. "
    "Multa simulada: Q{amount:.2f}. Mensaje de PROTOTIPO, no es una notificacion oficial."
)

EMAIL_SUBJECT_TEMPLATE = "[SIMULADO] Notificacion de infraccion de transito - Placa {plate}"

EMAIL_BODY_TEMPLATE = """Estimado/a {owner_name}:

Este es un mensaje SIMULADO generado por un prototipo de hackathon (SyncTrack).
No es una notificacion oficial ni proviene de una entidad gubernamental real.
(Nota: este sistema no tiene acceso real a datos de titulares de placas --
ese cruce de informacion solo lo tiene una entidad como la SAT/RENAP via el
impuesto de circulacion. El nombre de arriba es simulado.)

Placa: {plate}
Velocidad detectada: {speed:.0f} km/h
Limite de la via: {limit:.0f} km/h
Fecha/hora: {timestamp}
Multa simulada: Q{amount:.2f}

-- SyncTrack (prototipo de hackathon, no oficial) --
"""


@dataclass
class MockNotification:
    channel: str  # "sms" | "email"
    to: str
    subject: str | None
    body: str


def generate_notifications(fine, phone="+502 5555-0000", email="titular@ejemplo.com"):
    fmt_kwargs = dict(
        owner_name=fake_owner_name(fine.plate),
        plate=fine.plate,
        speed=fine.speed_kmh,
        limit=fine.limit_kmh,
        timestamp=fine.timestamp,
        amount=fine.fine_amount_gtq,
    )
    return [
        MockNotification(
            channel="sms",
            to=phone,
            subject=None,
            body=SMS_TEMPLATE.format(**fmt_kwargs),
        ),
        MockNotification(
            channel="email",
            to=email,
            subject=EMAIL_SUBJECT_TEMPLATE.format(plate=fine.plate),
            body=EMAIL_BODY_TEMPLATE.format(**fmt_kwargs),
        ),
    ]


def send_fine_notifications(fine, notifications, evidence_path=None):
    """Best-effort real email delivery for the demo. SMS is never really
    sent (log-only, see MockNotification above). Never raises -- a failed
    send must not crash the video-processing pipeline."""
    if not (GMAIL_USER and GMAIL_APP_PASSWORD):
        print("  (email real: GMAIL_USER/GMAIL_APP_PASSWORD no configurados en .env, se omite envio real)")
        return

    email_notif = next((n for n in notifications if n.channel == "email"), None)
    if email_notif is None:
        return

    msg = EmailMessage()
    msg["Subject"] = email_notif.subject
    msg["From"] = GMAIL_USER
    msg["To"] = DEMO_NOTIFY_EMAIL
    msg.set_content(email_notif.body)

    if evidence_path:
        try:
            with open(evidence_path, "rb") as f:
                msg.add_attachment(
                    f.read(), maintype="image", subtype="jpeg", filename="evidencia.jpg"
                )
        except OSError:
            pass

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"  (email real enviado a {DEMO_NOTIFY_EMAIL})")
    except Exception as exc:  # noqa: BLE001 -- demo pipeline must keep running
        print(f"  (email real: fallo el envio, se continua sin el: {exc})")
