# SyncTrack

## What This Is

SyncTrack es un prototipo de sistema de vigilancia de tránsito para una calle real de Zona 4, Ciudad de Guatemala, construido para un hackathon de impacto social. A partir de video grabado de esa calle, detecta vehículos y placas, estima la velocidad, y cuando se excede el límite genera automáticamente una multa simulada: notificación mock por SMS/correo y registro visible en un portal público estilo autoridad de tránsito.

## Core Value

Dado un video real grabado en la calle de Zona 4, el sistema debe detectar de principio a fin al menos un vehículo que exceda el límite de velocidad — leer la placa, calcular la velocidad, generar la multa y mostrarla en el portal — en una sola corrida de demo en vivo frente a los jueces del hackathon.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] El sistema puede ingerir un video grabado y procesarlo cuadro por cuadro
- [ ] El sistema detecta vehículos y localiza su placa en el video
- [ ] El sistema lee el texto de la placa (OCR) con formato de Guatemala
- [ ] El sistema estima la velocidad del vehículo a partir del video
- [ ] El sistema compara la velocidad estimada contra un límite configurable de la vía
- [ ] El sistema genera automáticamente un registro de multa (placa, velocidad, límite, timestamp, evidencia) cuando se excede el límite
- [ ] El sistema genera una notificación simulada (mock) de SMS y de correo por cada multa
- [ ] Existe un portal web tipo "autoridad de tránsito" donde se listan placas registradas y sus multas
- [ ] El flujo completo (video → detección → multa → portal) se puede ejecutar en una demo en vivo

### Out of Scope

- Integración con cámaras en vivo (RTSP/USB/IP) — no hay tiempo ni hardware; se usa video pregrabado
- Envío real de SMS/correo (Twilio, SendGrid, etc.) — se simula/mockea para evitar credenciales y costos bajo presión de tiempo
- Integración con un ente gubernamental real (SAT u otro) — es un prototipo de hackathon, no un sistema con autoridad legal
- Autenticación de usuarios y hardening de seguridad de producción — fuera de alcance para un prototipo de horas
- Soporte multi-región/multi-formato de placas — se enfoca solo en el formato de Guatemala

## Context

- Es una entrega de hackathon que exige un "proyecto de impacto social"
- Motivación: el exceso de velocidad en calles de Zona 4, Ciudad de Guatemala pone en riesgo a los peatones; el proyecto busca demostrar cómo la automatización puede detectar y disuadir esta conducta
- El usuario ya grabó varios clips de video reales en esa misma calle, desde distintos ángulos/pasadas de vehículos
- Presión de tiempo extrema: solo horas disponibles antes de la demo
- La demo debe mostrar el flujo completo en vivo ante los jueces (no basta con componentes aislados)

## Constraints

- **Tiempo**: Solo horas hasta la entrega — priorizar un MVP funcional sobre pulido o robustez
- **Stack técnico**: Python (FastAPI + OpenCV + YOLOv8 + OCR tipo PaddleOCR/EasyOCR)
- **Alcance**: Prototipo/simulación — sin hardware real, sin integración gubernamental real
- **Fuente de video**: Clips pregrabados de la calle en Zona 4 (no cámara en vivo)
- **Notificaciones**: Simuladas/mock — sin proveedores reales de SMS/correo
- **Región**: Guatemala — formato de placas y límites de velocidad locales
- **Control de versiones**: Cada paso de implementación, por pequeño que sea, debe quedar en su propio commit de git (pedido explícito del usuario)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Prototipo/simulación, no sistema de producción | Es un proyecto de hackathon de impacto social, no un sistema gubernamental real | — Pending |
| Python + OpenCV/YOLOv8 + OCR | Ecosistema de visión por computadora más maduro para desarrollo rápido bajo presión de tiempo | — Pending |
| Video pregrabado en vez de cámara en vivo | Ya existen clips reales grabados en Zona 4; integrar RTSP en vivo tomaría tiempo que no hay | — Pending |
| Notificaciones simuladas (mock) | Evita depender de cuentas/credenciales reales (Twilio, SendGrid) bajo presión de tiempo | — Pending |
| Commits atómicos por cada paso | Petición explícita del usuario, para dejar rastro completo del progreso | — Pending |

---
*Last updated: 2026-07-16 after initialization*
