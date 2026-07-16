# Requirements: SyncTrack

**Defined:** 2026-07-16
**Core Value:** Dado un video real grabado en la calle de Zona 4, el sistema debe detectar de principio a fin al menos un vehículo que exceda el límite de velocidad — leer la placa, calcular la velocidad, generar la multa y mostrarla en el portal — en una sola corrida de demo en vivo frente a los jueces del hackathon.

## v1 Requirements

### Ingesta de Video

- [ ] **INGEST-01**: El sistema puede leer un video pregrabado cuadro por cuadro

### Detección y Seguimiento de Vehículos

- [ ] **DETECT-01**: El sistema detecta vehículos en cada cuadro usando un modelo preentrenado (sin entrenamiento propio)
- [ ] **DETECT-02**: El sistema mantiene el mismo identificador de vehículo (tracking) a través de múltiples cuadros consecutivos

### Placa (Localización + OCR)

- [ ] **PLATE-01**: El sistema localiza la región de la placa dentro del recorte del vehículo detectado
- [ ] **PLATE-02**: El sistema lee el texto de la placa vía OCR y lo valida contra el formato de Guatemala (1 letra + 3 dígitos + 3 letras)

### Velocidad

- [ ] **SPEED-01**: El sistema calcula la velocidad del vehículo usando una distancia de referencia real calibrada manualmente contra el video y el tiempo transcurrido entre dos puntos de cruce
- [ ] **SPEED-02**: El sistema compara la velocidad estimada contra un límite de velocidad configurable (un solo valor para el tramo grabado en v1)

### Multas y Notificaciones

- [ ] **FINE-01**: El sistema genera automáticamente un registro de multa (placa, velocidad, límite, timestamp, cuadro de evidencia) cuando se excede el límite
- [ ] **NOTIF-01**: El sistema genera (sin enviar) el contenido de una notificación simulada de SMS y de correo por cada multa, marcada explícitamente como "SIMULADO"

### Portal

- [ ] **PORTAL-01**: Existe un portal web que lista las placas registradas y sus multas (placa, fecha/hora, velocidad medida, límite, monto, miniatura de evidencia)
- [ ] **PORTAL-02**: El portal muestra en todo momento un aviso visible de "SIMULADO — prototipo de hackathon, no es una entidad gubernamental"

### Demo End-to-End

- [ ] **DEMO-01**: El flujo completo (ingesta → detección → OCR → velocidad → multa → notificación → portal) corre en una sola pasada continua y en vivo

## v2 Requirements

Deferido a después del hackathon (solo si sobra tiempo tras validar v1).

### Diferenciadores

- **STATS-01**: Vista de estadísticas/dashboard de violaciones (conteo, velocidad promedio vs. límite)
- **OVERLAY-01**: Reproducción de video anotado con bounding boxes y velocidad superpuesta
- **ZONE-01**: Configuración de zona/límite simulada (ej. "zona escolar") en vez de límite único hardcodeado
- **PORTAL-03**: Búsqueda/filtro de placas o fecha en el portal
- **PLATE-03**: Badge de confianza de OCR por lectura

## Out of Scope

Excluido explícitamente. Documentado para prevenir scope creep durante el hackathon.

| Feature | Reason |
|---------|--------|
| Envío real de SMS/correo (Twilio, SendGrid, etc.) | Riesgo legal/ético real (implica una multa legal real a un posible titular inocente), no solo costo de tiempo |
| Integración con entidad gubernamental real (SAT/PROVIAL/RENAP) | Implicaría autoridad legal que este prototipo no tiene; riesgo de suplantación |
| Búsqueda de identidad del propietario (placa → nombre/dirección real) | Exposición real de datos personales de terceros — "mission creep" documentado de sistemas ALPR reales |
| Reconocimiento facial/biométrico de ocupantes | Categoría de sensibilidad distinta y fuera de alcance de un prototipo de velocidad/placas |
| Cámara en vivo / RTSP / IP | Sin hardware ni tiempo disponible; ya excluido en PROJECT.md |
| Procesamiento de pagos reales | Implicaría transacciones financieras reales, fuera de cualquier alcance razonable de hackathon |
| Escalamiento automatizado (suspensión de licencia, puntos, listas de alerta) | Estas son consecuencias legales/administrativas reales; simularlas arriesga que el demo se lea como si reclamara autoridad regulatoria real |
| Publicar/exponer indiscriminadamente todas las placas visibles en el video | El video es de una calle pública real con terceros que no dieron consentimiento; el alcance se limita al/los vehículo(s) usados deliberadamente para la demo |
| Soporte multi-región / múltiples formatos de placa | Ya excluido en PROJECT.md — solo formato de Guatemala |
| Autenticación de usuarios / hardening de seguridad de producción | Fuera de alcance para un prototipo de horas |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Pending |
| DETECT-01 | Phase 1 | Pending |
| DETECT-02 | Phase 1 | Pending |
| PLATE-01 | Phase 2 | Pending |
| PLATE-02 | Phase 2 | Pending |
| SPEED-01 | Phase 3 | Pending |
| SPEED-02 | Phase 3 | Pending |
| FINE-01 | Phase 4 | Pending |
| NOTIF-01 | Phase 4 | Pending |
| PORTAL-01 | Phase 4 | Pending |
| PORTAL-02 | Phase 4 | Pending |
| DEMO-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12/12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-07-16*
*Last updated: 2026-07-16 after roadmap creation (traceability mapped to Phases 1-5)*
