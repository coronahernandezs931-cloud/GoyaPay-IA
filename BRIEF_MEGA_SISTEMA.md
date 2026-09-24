# Brief: Mega Sistema IA — Versión Comunidad

## Contexto

Tengo un sistema de agentes de voz con IA que ya funciona en producción para una inmobiliaria (repo: `santmun/sofia-voice-agent`). Ahora necesito convertirlo en una **plantilla reutilizable** que mis alumnos de Horizontes IA puedan usar para vender este servicio a cualquier tipo de negocio.

El repo de YouTube (`sofia-voice-agent`) es el código gratis. Este nuevo repo (`mega-sistema-ia`) es el producto de paga con herramientas de setup rápido y personalización.

## Lo que ya existe (repo base)

El sistema actual tiene:
- **Backend en Python + Modal** con 8 endpoints (search, create lead, book visit, update lead, post-call summary, webhooks, health, trigger outbound)
- **Retell AI** para el agente de voz (inbound + outbound con dynamic variables)
- **Twilio** para telefonía vía SIP trunk
- **Notion** como CRM (3 bases de datos: propiedades, leads, historial de llamadas)
- **Cal.com** para agendar citas
- **Claude Sonnet 4.5** para análisis post-llamada (resumen + lead scoring)
- **Next.js + shadcn/ui** dashboard con analíticas
- **Worker outbound** con cron cada hora en Modal

Todo está desplegado y funcional. El número es +16624938662 conectado vía SIP trunk.

## Lo que necesito construir

### 1. Archivo de configuración central: `sofia.config.yaml`

Un solo archivo donde el alumno define TODO lo específico del negocio. El sistema lee este archivo y se adapta. Ejemplo de estructura:

```yaml
business:
  name: "Clínica Dental Sonríe"
  industry: "dental"          # Clave para seleccionar template de prompt
  timezone: "America/Mexico_City"
  phone: "+525512345678"
  
agent:
  name: "Ana"
  voice_id: "cartesia-Sofia"  # ID de voz de Retell
  language: "es-419"
  personality: "amable, profesional, empática"
  
crm:
  # Campos del "producto" que vende el negocio
  product_name: "Tratamientos"    # Cómo se llama la tabla de productos
  product_fields:
    - name: "Tratamiento"
      type: "title"
    - name: "Precio"
      type: "number"
      format: "dollar"
    - name: "Duración"
      type: "rich_text"
    - name: "Categoría"
      type: "select"
      options: ["Limpieza", "Ortodoncia", "Implantes", "Blanqueamiento"]
      
  # Campos adicionales para leads (además de los base)
  lead_extra_fields:
    - name: "Tratamiento de interés"
      type: "select"
      options: ["Limpieza", "Ortodoncia", "Implantes"]
    - name: "Urgencia"
      type: "select"
      options: ["Urgente", "Esta semana", "Este mes", "Solo explorando"]

branding:
  primary_color: "#06b6d4"       # Color de acento del dashboard
  logo_text: "Sonríe"            # Texto del logo en sidebar
  dashboard_title: "Panel de Control"

credentials:
  # El alumno llena esto y el setup las configura en todos lados
  retell_api_key: ""
  twilio_account_sid: ""
  twilio_auth_token: ""
  twilio_phone_number: ""
  notion_api_key: ""
  notion_parent_page_id: ""
  cal_api_key: ""
  cal_event_type_id: ""
  anthropic_api_key: ""
```

### 2. Setup automatizado: skill `/setup`

Un CLAUDE.md con un skill que al ejecutar `/setup`:

1. Lee `sofia.config.yaml`
2. Valida que todas las credenciales estén llenas
3. Crea las bases de datos en Notion con los campos del config (productos, leads, llamadas)
4. Genera el prompt del agente usando el template de la industria + datos del config
5. Crea el LLM y el Agente en Retell (inbound + outbound)
6. Crea el SIP trunk en Twilio y conecta el número
7. Importa el número en Retell y lo asigna a los agentes
8. Crea el secret en Modal y despliega
9. Genera el `.env` y `.env.local` del dashboard
10. Mensaje final con resumen de todo lo configurado

### 3. Librería de prompts por industria

Directorio `prompts/` con templates pre-hechos. Cada template define:
- Prompt del agente inbound
- Prompt del agente outbound
- Campos específicos del CRM para esa industria
- Productos/servicios de ejemplo para cargar

Industrias a cubrir:
1. **inmobiliaria** — Lo que ya tenemos (propiedades, zonas, visitas)
2. **dental** — Tratamientos, urgencias, seguimiento post-tratamiento
3. **gimnasio** — Membresías, horarios de clases, pruebas gratuitas
4. **restaurante** — Reservaciones, menú, eventos especiales
5. **clinica** — Citas médicas, especialidades, seguros aceptados
6. **abogados** — Consultas iniciales, áreas de práctica, seguimiento de casos
7. **salon-belleza** — Servicios, estilistas, disponibilidad
8. **veterinaria** — Citas, vacunas, emergencias

### 4. Dashboard parametrizado

Que el dashboard tome del config:
- Color de acento (reemplaza amber/orange)
- Nombre del negocio en sidebar
- Nombre del agente
- Labels adaptados a la industria (en vez de "Propiedades" dice "Tratamientos" para dental)

### 5. Estructura del repo final

```
mega-sistema-ia/
├── sofia.config.yaml           # El alumno edita SOLO este archivo
├── CLAUDE.md                   # Skills de Claude Code (/setup, /customize, etc.)
├── prompts/
│   ├── inmobiliaria.yaml
│   ├── dental.yaml
│   ├── gimnasio.yaml
│   ├── restaurante.yaml
│   ├── clinica.yaml
│   ├── abogados.yaml
│   ├── salon-belleza.yaml
│   └── veterinaria.yaml
├── app/                        # Backend (igual que el original pero parametrizado)
├── dashboard/                  # Frontend (parametrizado con config)
├── scripts/
│   └── setup.py                # Script de setup que el skill ejecuta
└── README.md                   # Instrucciones para alumnos de la comunidad
```

## Notas importantes

- El repo base es `santmun/sofia-voice-agent` — clónalo como punto de partida
- Stack: Python + Modal (backend), Next.js + shadcn/ui (dashboard)
- Todos los servicios tienen plan gratis para empezar
- El setup debe funcionar end-to-end: un alumno llena el YAML, corre `/setup`, y en 5 minutos tiene todo funcionando
- El diseño del dashboard es dark mode con tipografía premium (Playfair Display italic + Inter)
- Santi es el creador — su comunidad es Horizontes IA (iahorizontesacademy.com)
