# 🚀 GoyaPay AI — Asistente Autónomo de Voz, Finanzas Web3 & Business Manager

**GoyaPay AI** es una plataforma integral de finanzas, liquidación de adeudos y cobros asistida por Inteligencia Artificial conversacional de voz en tiempo real. Diseñada para eliminar la fricción en la gestión y liquidación de adeudos (universitarios, trámites y negocios), integra infraestructura multicadena Web3 de última generación (**Avalanche C-Chain**, **Pollar Smart Wallet en Stellar Soroban** y hardware criptográfico **Tangem Cold Wallet NFC**), pasarelas bancarias tradicionales (**Stripe Checkout Oficial** y **SPEI Banxico**), y análisis financiero automatizado con **Notion CRM**.

---

## 🌟 Pilares y Capacidades Principales

1. **🎙️ Agente Autónomo de Voz 24/7 (Retell AI + Cartesia/Claude):**
   - Diálogo fluido con latencia ultrabaja (<800ms) y acento mexicano natural.
   - Consulta adeudos en tiempo real, registra transacciones y despacha órdenes de cobro multicanal.
   - Disponible vía telefonía SIP (Twilio) y mediante Llamada Web directa (WebRTC) desde el navegador.

2. **❄️ Liquidaciones Web3 & Multicadena (Avalanche + Stellar + Tangem):**
   - **Avalanche C-Chain Mainnet:** Liquidación instantánea con tarifas mínimas de gas, verificación on-chain e interoperabilidad EVM.
   - **Pollar Smart Wallet (Stellar Soroban):** Contratos inteligentes sobre Stellar para transferencias descentralizadas instantáneas con alta eficiencia energética.
   - **Tangem Cold Wallet (Hardware NFC EAL6+):** Firma criptográfica mediante Universal Links y chips de seguridad física militar.

3. **💳 Pasarelas Bancarias y Rieles Tradicionales:**
   - **Stripe Checkout Oficial (Tarjetas Bancarias):** Pasarela certificada PCI-DSS Nivel 1 compatible con Visa, Mastercard, AMEX, Apple Pay y Google Pay.
   - **Transferencia SPEI Banxico:** Asignación de CLABE interbancaria (STP) con conciliación automatizada.

4. **💼 GoyaPay Business Manager (Auditoría Financiera & CRM en Notion):**
   - Base de datos en **Notion** sincronizada bidireccionalmente.
   - Cálculo en vivo de KPIs: Ingresos cobrados, adeudos pendientes, balance neto operativo, tasa de cobranza efectiva, ticket promedio y diagnóstico de solvencia con IA.

5. **📧 Notificaciones Transaccionales Instantáneas (Resend):**
   - Despacho automático de enlaces de pago seguros y recibos formales con diseño responsivo a los correos de los clientes.

---

## 🏗️ Arquitectura del Sistema

```mermaid
flowchart TD
    User([Usuario / Cliente]) -->|Llamada Telefónica / WebRTC| Retell[Retell AI Voice Agent]
    User -->|Portal Web / Checkout| WebApp[Plataforma Web en Vercel]
    
    Retell -->|Function Calling / Webhooks| Modal[Backend Serverless en Modal Python]
    WebApp -->|API REST Serverless| Modal
    
    Modal -->|Lectura / Escritura de Adeudos| Notion[(Notion CRM Ledger)]
    Modal -->|Envío de Links y Recibos| Resend[Resend Email API]
    Modal -->|Sesiones y Verificación| Stripe[Stripe Checkout API]
    Modal -->|Contratos Inteligentes| Pollar[Pollar Smart Wallet / Stellar Soroban]
    Modal -->|Verificación On-Chain| Avax[Avalanche C-Chain RPC]
    
    WebApp -->|Firma Criptográfica NFC| TangemApp[Tangem Cold Wallet App]
    WebApp -->|Acreditación con Tarjeta| Stripe
    WebApp -->|Transferencia Interbancaria| SPEI[Banco Receptor STP / Banxico]
```

---

## 📁 Estructura del Repositorio

```text
├── backend_modal.py          # Backend serverless en Modal con endpoints de Voz, Notion, Web3 y Stripe
├── checkout-web/             # Frontend web responsivo alojado en Vercel (Simulador de voz, Checkout y Business Manager)
│   ├── public/
│   │   ├── index.html        # Portal principal interactivo con audio visualizer, chat de Sofía y KPIs
│   │   ├── checkout.html     # Pasarela multicadena (Avalanche, Pollar, Tangem, SPEI, Stripe)
│   │   └── package.json
├── setup_twilio_trunk.py     # Configuración automatizada del SIP Trunk en Twilio hacia Retell
├── clear_notion_data.py      # Utilidad para resetear y poblar pagos de prueba en Notion CRM
├── test_full_suite.py        # Suite de pruebas automatizadas de integración
├── pyproject.toml            # Definición de dependencias y paquetes de Python
├── .env.example              # Plantilla sanitizada de variables de entorno
├── goyapay-ai-especificacion.md # Especificación técnica profunda de la arquitectura
└── DEMO_PITCH_GUIDE.md       # Guía paso a paso para la demostración y pitch en vivo
```

---

## 🛠️ Tecnologías Utilizadas

- **Lenguaje:** Python 3.11+
- **Computación Serverless:** [Modal](https://modal.com)
- **Voz y Audio IA:** [Retell AI](https://retellai.com) & [Cartesia](https://cartesia.ai)
- **Telefonía SIP:** [Twilio](https://twilio.com)
- **Base de Datos / CRM:** [Notion API](https://developers.notion.com)
- **Blockchain & Smart Wallets:**
  - [Avalanche C-Chain](https://avax.network)
  - [Pollar Smart Wallet (Stellar Soroban)](https://pollar.org)
  - [Tangem Cold Wallet](https://tangem.com)
- **Pasarelas Bancarias:** [Stripe](https://stripe.com) & STP / SPEI Banxico
- **Email Transaccional:** [Resend](https://resend.com)
- **Hosting Frontend:** [Vercel](https://vercel.com)

---

## ⚙️ Configuración Rápida

### 1. Clonar el repositorio
```bash
git clone https://github.com/coronahernandezs931-cloud/GoyaPay-IA.git
cd GoyaPay-IA
```

### 2. Configurar variables de entorno
Copia la plantilla `.env.example` y completa tus credenciales:
```bash
cp .env.example .env
```

Variables requeridas en el archivo `.env`:
```ini
# Retell AI (Voz y Telefonía)
RETELL_API_KEY=tu_retell_api_key
RETELL_AGENT_ID=tu_agent_id

# Twilio SIP Trunk
TWILIO_ACCOUNT_SID=tu_twilio_account_sid
TWILIO_AUTH_TOKEN=tu_twilio_auth_token
TWILIO_PHONE_NUMBER=tu_numero_twilio

# Notion CRM & Ledger
NOTION_API_KEY=tu_notion_integration_token
NOTION_DATABASE_ID=tu_notion_database_id

# Resend Email
RESEND_API_KEY=tu_resend_api_key

# Stripe Checkout
STRIPE_SECRET_KEY=sk_test_tu_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_tu_stripe_publishable_key

# Web3 & Blockchain Multi-chain
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
POLLAR_TOKEN=tu_pollar_token

# URLs de Producción
VERCEL_CHECKOUT_URL=https://checkout-web-seven.vercel.app/checkout
```

### 3. Desplegar el Backend en Modal
```bash
pip install modal
modal setup
modal deploy backend_modal.py
```

### 4. Ejecutar Pruebas de Integración
Valida que todos los servicios y conexiones operen al 100%:
```bash
python test_full_suite.py
```

---

## 🎥 Guía de Pitch y Demo en Vivo
Para ejecutar una demostración guiada del ecosistema (consulta por voz en vivo, análisis financiero en Notion, liquidación en Avalanche / Pollar / Tangem / Stripe), consulta el archivo [DEMO_PITCH_GUIDE.md](DEMO_PITCH_GUIDE.md).

---

## 📄 Licencia
Proyecto desarrollado para **Goya Hack 2026** (Track AI & Fintech / Web3). Distribuido bajo la Licencia MIT.
