# 🚀 GoyaPay AI — Asistente Autónomo de Voz, Pagos Multibanco & Business Manager

**GoyaPay AI** es una plataforma integral de finanzas y pagos asistida por Inteligencia Artificial conversacional de voz en tiempo real. Diseñada para eliminar la fricción en la gestión y liquidación de adeudos (universitarios, trámites y negocios), integra hardware criptográfico de última generación (**Tangem Cold Wallet NFC**), pasarelas bancarias tradicionales (**Stripe Checkout Oficial** y **SPEI Banxico**), análisis financiero automatizado con **Notion CRM** y difusión de contenidos en redes sociales mediante **Zernio API**.

---

## 🌟 Características Principales

1. **🎙️ Agente de Voz Inteligente 24/7 (Retell AI + Cartesia/Claude):**
   - Diálogo fluido con latencia ultrabaja (<800ms) y acento mexicano natural.
   - Consulta adeudos en tiempo real, registra transacciones y despacha órdenes de pago multicanal.
   - Disponible vía telefonía SIP (Twilio) y mediante Llamada Web directa (WebRTC) sin costo de telefonía.

2. **💳 Pasarela de Pago Multibanco 3 en 1:**
   - **Tangem Cold Wallet (Web3 NFC):** Firma criptográfica mediante Universal Links oficiales y conexión por hardware EAL6+.
   - **Stripe Checkout Oficial (Tarjetas Bancarias):** Pasarela de Nivel 1 compatible con Visa, Mastercard, AMEX, Apple Pay y Google Pay.
   - **Transferencia SPEI Banxico:** Asignación de CLABE interbancaria (STP) con conciliación automatizada.

3. **💼 GoyaPay Business Manager (Auditoría Financiera & CRM):**
   - Base de datos en **Notion** sincronizada bidireccionalmente.
   - Cálculo en vivo de KPIs: Ingresos cobrados, adeudos pendientes, tasa de cobranza efectiva, ticket promedio y salud financiera.

4. **🌐 Omnichannel Social Media Suite (Zernio API):**
   - Auditoría de canales digitales en **TikTok** y **YouTube**.
   - Métricas de audiencia: visualizaciones orgánicas, reacciones, engagement rate y pipeline de publicaciones.
   - **Programador de Videos Directo:** Publicación inmediata o programada de videos en redes sociales con un solo clic.

5. **📧 Notificaciones Transaccionales Instantáneas (Resend):**
   - Despacho automático de enlaces de pago seguros y recibos formales con diseño responsivo.

---

## 🏗️ Arquitectura del Sistema

`mermaid
flowchart TD
    User([Usuario / Cliente]) -->|Llamada Telefónica / Web Call| Retell[Retell AI Voice Agent]
    User -->|Navegador Web / Checkout| WebApp[Plataforma Web en Vercel]
    
    Retell -->|Function Calling / Webhooks| Modal[Backend Serverless en Modal Python]
    WebApp -->|API Requests| Modal
    
    Modal -->|Lectura / Escritura de Adeudos| Notion[(Notion CRM Database)]
    Modal -->|Envío de Links y Recibos| Resend[Resend Email API]
    Modal -->|Creación y Verificación de Sesiones| Stripe[Stripe Checkout API]
    Modal -->|Analítica y Programación de Videos| Zernio[Zernio Social API]
    
    WebApp -->|Firma Criptográfica NFC| TangemApp[Tangem Cold Wallet App]
    WebApp -->|Acreditación de Tarjeta| Stripe
    WebApp -->|Transferencia Interbancaria| SPEI[Banco Receptor STP / Banxico]
`

---

## 📁 Estructura del Repositorio

`	ext
├── backend_modal.py          # Servidor serverless en Modal con todos los endpoints y lógica de negocio
├── setup_twilio_trunk.py     # Configuración automatizada del SIP Trunk en Twilio hacia Retell
├── clear_notion_data.py      # Utilidad para resetear y poblar pagos de prueba en Notion CRM
├── test_full_suite.py        # Suite de pruebas automatizadas de integración
├── pyproject.toml            # Definición de dependencias y paquetes de Python (uv / pip)
├── .env.example              # Plantilla sanitizada de variables de entorno
├── goyapay-ai-especificacion.md # Especificación técnica profunda de la arquitectura
└── DEMO_PITCH_GUIDE.md       # Guía paso a paso para la demostración y pitch en vivo
`

---

## 🛠️ Requisitos y Tecnologías

- **Lenguaje:** Python 3.11+
- **Computación Serverless:** [Modal](https://modal.com)
- **Voz y Audio:** [Retell AI](https://retellai.com)
- **Base de Datos / CRM:** [Notion API](https://developers.notion.com)
- **Email:** [Resend](https://resend.com)
- **Pasarela de Tarjetas:** [Stripe](https://stripe.com)
- **Cold Wallet:** [Tangem](https://tangem.com)
- **Redes Sociales:** [Zernio](https://zernio.com)
- **Hosting Frontend:** [Vercel](https://vercel.com)

---

## ⚙️ Configuración Rápida

### 1. Clonar el repositorio
`ash
git clone https://github.com/coronahernandezs931-cloud/GoyaPay-IA.git
cd GoyaPay-IA
`

### 2. Configurar variables de entorno
Copia la plantilla .env.example y completa tus credenciales:
`ash
cp .env.example .env
`

Variables requeridas en el archivo .env:
`ini
# Retell AI
RETELL_API_KEY=tu_retell_api_key

# Notion CRM
NOTION_API_KEY=tu_notion_integration_token
NOTION_DATABASE_ID=tu_notion_database_id

# Resend Email
RESEND_API_KEY=tu_resend_api_key

# Stripe
STRIPE_SECRET_KEY=sk_test_tu_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_tu_stripe_publishable_key

# Zernio
ZERNIO_API_KEY=sk_tu_zernio_api_key

# URLs de Producción
VERCEL_CHECKOUT_URL=https://tu-dominio.vercel.app/checkout
`

### 3. Desplegar el Backend en Modal
Instala Modal y despliega la aplicación serverless:
`ash
pip install modal
modal setup
modal deploy backend_modal.py
`

### 4. Ejecutar Pruebas de Integración
Valida que todos los servicios y conexiones operen al 100%:
`ash
python test_full_suite.py
`

---

## 🎥 Guía de Pitch y Demo en Vivo
Para ejecutar una demostración guiada del ecosistema (consulta por voz, análisis de negocio, programación de video en TikTok/YouTube y pago con Tangem / Stripe), consulta el archivo [DEMO_PITCH_GUIDE.md](DEMO_PITCH_GUIDE.md).

---

## 📄 Licencia
Proyecto desarrollado para **Goya Hack 2026** (Track AI & Fintech). Distribuido bajo la Licencia MIT.
