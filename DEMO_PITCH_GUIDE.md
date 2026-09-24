# GoyaPay AI — Demo & Guía de Pitch para Goya Hack 2026
**Track AI • Reto Patrocinado Tangem**

---

## 🎯 Resumen del Ecosistema Construido
Se ha desplegado y orquestado un sistema autónomo de cobranza y pagos asistidos por voz e integrados a la infraestructura de Tangem y Notion:

1. **Base de Datos CRM en Notion (`GoyaPay_Pagos`):**
   - Base de datos creada dinámicamente vía API.
   - Id: `3e349bc5-0aa5-8193-b9a3-e8b13e9e20d2`
   - Campos: `Concepto`, `Telefono`, `Usuario`, `Monto`, `Estado` (`pendiente` -> `enlace_enviado` -> `pagado`), `Correo`.

2. **Backend Serverless en Modal (`goyapay-voice-backend`):**
   - Desplegado en `https://coronahernandezs931--goyapay-voice-backend-*.modal.run`.
   - Microservicios de consulta de deudas, registro de nuevos cobros, generación de links y envío de correos vía Resend (`onboarding@resend.dev`).
   - Webhook de confirmación de pago Tangem que actualiza en tiempo real el estado en Notion a `pagado`.

3. **Agente de Voz en Retell AI:**
   - LLM: `llm_92dc57bee1f0ac63a01d247f5003` (Claude 3.5 Sonnet / 4.5 con acento y calidez mexicana formal).
   - Agent ID: `agent_14126a001a6e0fb2438a6765ed` (Voz: `cartesia-Sofia`).
   - Herramientas conectadas directamente al backend de Modal:
     - `consultar_pagos_notion`
     - `registrar_pago_notion`
     - `enviar_correo_pago`
     - `end_call`

4. **Frontend & Simulador Web en Vercel:**
   - **Simulador de Voz en Vivo:** [https://checkout-web-seven.vercel.app](https://checkout-web-seven.vercel.app)
   - **Pasarela de Checkout TangemPay:** [https://checkout-web-seven.vercel.app/checkout](https://checkout-web-seven.vercel.app/checkout)

---

## 🎬 Flujo de Demostración para el Pitch (Split-Screen)

### 1. Preparación de Pantalla (Pestañas Abiertas):
- **Pantalla Izquierda:** [Simulador de Voz GoyaPay](https://checkout-web-seven.vercel.app) con tu micrófono activado.
- **Pantalla Derecha Superior:** Base de datos en Notion (visualizando el registro de `Sergio Ethan Corona Hernández`).
- **Pantalla Derecha Inferior:** Bandeja de correo `coronahernandezs931@gmail.com`.

### 2. El Diálogo con el Agente:
1. Da clic en el botón azul del micrófono en [checkout-web-seven.vercel.app](https://checkout-web-seven.vercel.app).
2. **GoyaPay:** *"¡Hola Sergio Ethan! Te hablo de GoyaPay AI en colaboración con Tangem. ¿En qué puedo apoyarte hoy?"*
3. **Tú:** *"Hola, quisiera saber si tengo algún adeudo o pago pendiente por liquidar."*
4. **GoyaPay:** Ejecuta `consultar_pagos_notion` en tiempo real y responde:
   *"Detecto que tienes un concepto pendiente de 'Credencial de Biblioteca' por 120 pesos mexicanos. ¿Deseas que te envíe el enlace de pago seguro con TangemPay a tu correo?"*
5. **Tú:** *"Sí, por favor, envíamelo a mi correo."*
6. **GoyaPay:** Ejecuta `enviar_correo_pago`. Recibirás el correo instantáneamente en Gmail y el estado en Notion cambiará a `enlace_enviado`.

### 3. El Cierre con TangemPay:
1. Abre el correo o ve al checkout con los parámetros del adeudo.
2. Da clic en **"Confirmar y Pagar con TangemPay"**.
3. El frontend invoca la API serverless de Modal:
   - La pantalla muestra **"¡Pago Autorizado con Éxito!"**.
   - En Notion, el estado de la fila cambia inmediatamente a **PAGADO** en verde.
   - Redirecciona automáticamente a la app `tangem://` para el firmado criptográfico de la transacción.

---

## 🛡️ Integridad del Proyecto Sofía
- El proyecto original de Sofía (`sofia-voice-agent`) y su número telefónico de Twilio (`+12318670128`) permanecen **100% intactos e inalterados**.
- Para la evaluación y el pitch no necesitas tocar Twilio: el simulador web call de Retell permite que los jueces o tú interactúen con voz humana real y ultra-baja latencia directamente desde el navegador.
