# GoyaPay AI — Documentación Técnica de Arquitectura e Implementación
**Proyecto para Goya Hack 2026 (Track AI - Reto Patrocinado Tangem)**

---

## 1. Resumen Ejecutivo del Proyecto

**GoyaPay AI** es un asistente conversacional de voz autónomo y formal diseñado para eliminar la fricción en la consulta y gestión de pagos pendientes dentro del ecosistema universitario y financiero. 

El usuario puede llamar por teléfono a un número dedicado, interactuar mediante lenguaje natural en tiempo real para consultar sus adeudos o registrar nuevos gastos, y solicitar el envío de una orden de pago digitalizada. El agente procesa las solicitudes invocando herramientas externas (*Function Calling*), consulta y actualiza la base de datos en **Notion** en tiempo real, y envía un correo electrónico dinámico mediante **Resend** con un enlace directo a una interfaz de cobro en **Vercel** integrada con **TangemPay**.

---

## 2. Arquitectura General del Sistema

```
                         +------------------------+
                         |    Usuario (Llamada)   |
                         +-----------+------------+
                                     | (Voz en tiempo real)
                                     v
                         +------------------------+
                         |       Retell AI        |
                         | (Agente Conversacional)|
                         +-----------+------------+
                                     |
                                     | (Webhooks / Custom Tools)
                                     v
                         +------------------------+
                         |      Backend Modal     |
                         | (Python / Serverless)  |
                         +-----+------------+-----+
                               |            |
             +-----------------+            +-----------------+
             | (API REST)                                     | (Envío de correo)
             v                                                v
   +-------------------+                            +-------------------+
   |   Notion API      |                            |    Resend API     |
   | (Base de Datos)   |                            | (Servicio Email)  |
   +---------+---------+                            +---------+---------+
             ^                                                |
             |                                                v
             | (Actualización a "Pagado")           +-------------------+
             +--------------------------------------| Checkout Vercel   |
                                                    |  (TangemPay Web)  |
                                                    +-------------------+
```

### Componentes del Stack Tecnológico:
1. **Orquestación de Voz AI:** **Retell AI** (Procesamiento de audio de latencia ultrabaja y motor de *Function Calling*).
2. **Cómputo Serverless / Backend:** **Modal** (Microservicios en Python de alta disponibilidad y ejecución bajo demanda).
3. **Base de Datos Visiva:** **Notion API** (Gestión de usuarios y tabla de pagos con actualización dinámica de estados).
4. **Notificaciones:** **Resend API** (Generación de plantillas HTML y despacho instantáneo de correos transaccionales).
5. **Checkout & Wallet:** **Vercel** + **TangemPay** (Interfaz web ligera de confirmación y enlace hacia la app móvil de Tangem).

---

## 3. Estructura de la Base de Datos en Notion

Crea una base de datos de tipo **Tabla (Database)** en Notion nombrada `GoyaPay_Pagos` con las siguientes propiedades:

| Nombre de la Propiedad | Tipo en Notion | Descripción / Valores de ejemplo |
| :--- | :--- | :--- |
| `Concepto` | Title (Título) | `Inscripción Goya Hack`, `Revalidación de Credencial` |
| `Teléfono` | Phone / Text | `7772310427` (Últimos 10 dígitos) |
| `Usuario` | Text | `Sergio Ethan Corona Hernández` |
| `Monto` | Number (Número) | `50.00` (Moneda: MXN) |
| `Estado` | Select (Selección) | Opción 1: `pendiente`, Opción 2: `pagado`, Opción 3: `enlace_enviado` |
| `Correo` | Email | `coronahernandezs931@gmail.com` |
| `Fecha Registro` | Date | Fecha y hora de creación automática |

---

## 4. Prompt de Sistema para Retell AI (GoyaPay AI)

Configura este prompt en el apartado **System Prompt** de tu agente en el panel de Retell AI:

```text
Eres "GoyaPay AI", el asistente telefónico formal e inteligente de pagos para Goya Hack 2026. Tu trato es estrictamente profesional, respetuoso y ejecutivo.

REGLAS DE IDENTIFICACIÓN:
1. Inspecciona el parámetro 'user_phone' o el Caller ID de la llamada entrante.
2. Si el número contiene o termina en "7772310427", confía automáticamente en la identidad del usuario y salúdalo cordialmente por su nombre: Sergio Ethan Corona Hernández.
3. Si el número es distinto, saluda formalmente de manera neutral sin solicitar códigos complejos.

INSTRUCCIONES DE CONVERSACIÓN:

1. SALUDO INICIAL:
   "Bienvenido a GoyaPay AI. Es un gusto atenderle. ¿En qué le puedo asistir el día de hoy?"

2. CONSULTA DE PAGOS PENDIENTES:
   - Cuando el usuario solicite saber qué pagos o deudas tiene, invoca la herramienta 'consultar_pagos_notion'.
   - Si se detectan pagos pendientes: Menciona el concepto y el monto explícitamente. Ejemplo: "Registra un pago pendiente por el concepto 'Inscripción Goya Hack' por la cantidad de 50 pesos mexicanos." Pregúntale si desea proceder a liquidarlo en este momento.
   - Si NO se detectan pagos pendientes: Responde: "En este momento no registra ningún pago pendiente. ¿Le gustaría registrar un nuevo gasto o pago en el sistema?"

3. PROCESO DE PAGO Y ENVÍO DE CORREO:
   - Si el usuario confirma que desea pagar, pregúntale: "¿Desea que le envíe el enlace de autorización al correo registrado coronahernandezs931@gmail.com o prefiere proporcionar una dirección de correo distinta?"
   - Una vez confirmado el correo, ejecuta la herramienta 'enviar_correo_pago'.
   - Si la herramienta devuelve éxito: "Le he enviado el correo electrónico con el enlace de autorización a la dirección indicada. Quedo a su disposición."
   - Si la herramienta devuelve error: "Lo siento, ha ocurrido un error por saturación en el servicio de correo. Por favor intente nuevamente en unos momentos."

4. REGISTRO DE NUEVOS GASTOS / PAGOS:
   - Si el usuario solicita registrar un nuevo adeudo o gasto, pide el concepto y el monto en pesos.
   - Invoca la herramienta 'registrar_pago_notion'.
   - Al completar, responde: "El pago por el concepto de [concepto] por un monto de [monto] pesos ha sido registrado exitosamente en el sistema con estado pendiente."

5. NEGATIVA O CANCELACIÓN TEMPORAL:
   - Si el usuario indica que no desea pagar por ahora: "Entiendo perfectamente. Quedo a sus enteras órdenes para cuando decida realizar su pago. Que tenga un excelente día."
```

---

## 5. Código Backend en Modal (`backend_modal.py`)

A continuación se detalla el microservicio en Python para desplegar en **Modal**, utilizando `notion-client` para la base de datos y `resend` para las notificaciones:

```python
import os
import modal
from pydantic import BaseModel
from typing import Optional
from notion_client import Client as NotionClient
import resend

# 1. Definición de la Aplicación en Modal e Imagen con Dependencias
app = modal.App("goyapay-voice-backend")

image = modal.Image.debian_slim().pip_install(
    "fastapi",
    "pydantic",
    "notion-client",
    "resend"
)

# Variables de Entorno (Se pueden configurar vía Modal Secrets)
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "secret_tu_notion_token_aqui")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "tu_database_id_aqui")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_tu_resend_api_key_aqui")
VERCEL_CHECKOUT_URL = "https://goyapay.vercel.app/checkout"

# 2. Modelos de Datos (Pydantic) para las herramientas de Retell
class ConsultarPagosRequest(BaseModel):
    user_phone: str

class RegistrarPagoRequest(BaseModel):
    user_phone: str
    concepto: str
    monto: float
    usuario_nombre: Optional[str] = "Sergio Ethan Corona Hernández"

class EnviarCorreoRequest(BaseModel):
    email: str
    pago_id: str  # Page ID de Notion
    concepto: str
    monto: float

# 3. Endpoint: Consultar Pagos Pendientes en Notion
@app.function(image=image)
@modal.web_endpoint(method="POST")
def consultar_pagos_notion(data: ConsultarPagosRequest):
    notion = NotionClient(auth=NOTION_TOKEN)
    
    # Extraer últimos 10 dígitos del teléfono
    clean_phone = "".join(filter(str.isdigit, data.user_phone))[-10:]
    
    try:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "Teléfono",
                        "phone_number": {"contains": clean_phone} if clean_phone else {"is_not_empty": True}
                    },
                    {
                        "property": "Estado",
                        "select": {"equals": "pendiente"}
                    }
                ]
            }
        )
        
        results = response.get("results", [])
        if not results:
            return {"has_payments": False, "message": "No se encontraron pagos pendientes."}
        
        pagos = []
        for page in results:
            page_id = page["id"]
            props = page["properties"]
            
            # Extraer concepto
            concepto_items = props.get("Concepto", {}).get("title", [])
            concepto = concepto_items[0]["text"]["content"] if concepto_items else "Sin concepto"
            
            # Extraer monto
            monto = props.get("Monto", {}).get("number", 0.0)
            
            pagos.append({
                "pago_id": page_id,
                "concepto": concepto,
                "monto": monto
            })
            
        return {
            "has_payments": True,
            "pagos": pagos,
            "primer_pago": pagos[0]  # El agente usará este para sugerir el cobro
        }
    except Exception as e:
        return {"has_payments": False, "error": str(e)}

# 4. Endpoint: Registrar Nuevo Pago/Gasto en Notion
@app.function(image=image)
@modal.web_endpoint(method="POST")
def registrar_pago_notion(data: RegistrarPagoRequest):
    notion = NotionClient(auth=NOTION_TOKEN)
    clean_phone = "".join(filter(str.isdigit, data.user_phone))[-10:]
    
    try:
        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Concepto": {
                    "title": [{"text": {"content": data.concepto}}]
                },
                "Teléfono": {
                    "phone_number": clean_phone
                },
                "Usuario": {
                    "rich_text": [{"text": {"content": data.usuario_nombre}}]
                },
                "Monto": {
                    "number": float(data.monto)
                },
                "Estado": {
                    "select": {"name": "pendiente"}
                },
                "Correo": {
                    "email": "coronahernandezs931@gmail.com"
                }
            }
        )
        return {"status": "success", "page_id": new_page["id"], "message": "Pago registrado en Notion."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 5. Endpoint: Enviar Correo con Resend
@app.function(image=image)
@modal.web_endpoint(method="POST")
def enviar_correo_pago(data: EnviarCorreoRequest):
    resend.api_key = RESEND_API_KEY
    checkout_url = f"{VERCEL_CHECKOUT_URL}?page_id={data.pago_id}&monto={data.monto}&concepto={data.concepto}"
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f4f6f9; padding: 30px; margin: 0;">
        <div style="max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #0f172a; font-size: 24px; margin: 0;">GoyaPay AI</h1>
                <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Sistema de Pagos Inteligentes — UNAM Goya Hack 2026</p>
            </div>
            <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 24px; border-left: 4px solid #2563eb;">
                <p style="margin: 0 0 8px 0; color: #334155; font-size: 15px;"><b>Concepto:</b> {data.concepto}</p>
                <p style="margin: 0 0 8px 0; color: #334155; font-size: 15px;"><b>Monto a Liquidar:</b> ${data.monto:.2f} MXN</p>
                <p style="margin: 0; color: #334155; font-size: 15px;"><b>Método Sugerido:</b> TangemPay / Wallet Digital</p>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
                Estimado(a) usuario(a), haga clic en el siguiente botón para autorizar la transacción de manera segura utilizando su wallet de TangemPay:
            </p>
            <div style="text-align: center;">
                <a href="{checkout_url}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">
                    Autorizar Pago con TangemPay
                </a>
            </div>
            <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 30px 0 15px 0;">
            <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
                Este correo fue generado automáticamente durante la llamada telefónica con GoyaPay AI.
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        response = resend.Emails.send({
            "from": "GoyaPay AI <onboarding@resend.dev>",
            "to": [data.email],
            "subject": f"GoyaPay: Enlace de Autorización para {data.concepto}",
            "html": html_template
        })
        return {"status": "success", "email_id": response.get("id")}
    except Exception:
        # Retorna mensaje simulando saturación según requerimiento
        return {"status": "error", "message": "error por saturacion"}
```

---

## 6. Checkout Frontend en Vercel & Webhook de Confirmación

### Código `checkout.html` (Servido en Vercel)

Esta interfaz recibe la solicitud del correo, muestra los datos y al dar clic ejecuta la confirmación hacia la API de Notion:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoyaPay — Checkout TangemPay</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 flex items-center justify-center min-h-screen p-4">
    <div class="bg-slate-800 border border-slate-700 rounded-2xl p-8 max-w-md w-full shadow-2xl text-center">
        <div class="inline-block bg-blue-600/20 text-blue-400 p-3 rounded-full mb-4">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=" "></path></svg>
        </div>
        <h1 class="text-2xl font-bold mb-1">GoyaPay Checkout</h1>
        <p class="text-slate-400 text-sm mb-6">UNAM AI & Blockchain Hackathon 2026</p>

        <div class="bg-slate-900/60 rounded-xl p-4 text-left border border-slate-700/50 mb-6 space-y-2">
            <div><span class="text-xs text-slate-500 uppercase font-semibold">Concepto</span><p id="txtConcepto" class="font-medium text-slate-200">Cargando...</p></div>
            <div><span class="text-xs text-slate-500 uppercase font-semibold">Monto a Pagar</span><p id="txtMonto" class="text-2xl font-extrabold text-blue-400">$0.00 MXN</p></div>
            <div><span class="text-xs text-slate-500 uppercase font-semibold">Wallet Destino (TangemPay)</span><p class="text-xs font-mono text-slate-400 truncate">0x71C...42A_GoyaHack_Tangem</p></div>
        </div>

        <button id="btnPagar" onclick="procesarPago()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 px-6 rounded-xl transition duration-200 shadow-lg shadow-blue-600/30">
            Confirmar y Pagar con TangemPay
        </button>

        <div id="msgExito" class="hidden mt-6 p-4 bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 rounded-xl">
            ¡Pago Autorizado con Éxito! El estado ha sido actualizado a <b>PAGADO</b> en la base de datos de Notion.
        </div>
    </div>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const pageId = urlParams.get('page_id');
        const concepto = urlParams.get('concepto') || 'Inscripción Goya Hack';
        const monto = urlParams.get('monto') || '50.00';

        document.getElementById('txtConcepto').textContent = concepto;
        document.getElementById('txtMonto').textContent = `$${parseFloat(monto).toFixed(2)} MXN`;

        async function procesarPago() {
            const btn = document.getElementById('btnPagar');
            btn.disabled = true;
            btn.textContent = 'Procesando en TangemPay...';

            try {
                // Llamada al endpoint de confirmación que actualiza Notion
                const res = await fetch('/api/confirmar-pago', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ page_id: pageId })
                });

                document.getElementById('btnPagar').classList.add('hidden');
                document.getElementById('msgExito').classList.remove('hidden');
                
                // Intento opcional de abrir la app móvil de Tangem
                window.location.href = "tangem://";
            } catch (err) {
                alert("Error al procesar la actualización del pago.");
                btn.disabled = false;
                btn.textContent = 'Reintentar Pago';
            }
        }
    </script>
</body>
</html>
```

---

## 7. Plan de Acción de 76 Horas (Calendario BUIDL)

| Fase | Tarea Principal | Resultado Esperado |
| :--- | :--- | :--- |
| **Día 1 (Martes 22)** | Kickoff, configuración de la base de datos en Notion y credenciales en Modal. | Tabla `GoyaPay_Pagos` creada y despliegue inicial de Modal con endpoints probados con Curl. |
| **Día 2 (Miércoles 23)** | Configuración del Agente de Voz en Retell AI y vinculación de *Custom Tools*. | Realizar primera llamada de prueba al agente, validar saludo formal y consulta de saldos en Notion. |
| **Día 3 (Jueves 24)** | Integración de Resend para envío de correos y publicación del frontend en Vercel. | Flujo de punta a punta operando: Llamada -> Correo recibido -> Clic en Checkout -> Estado en Notion cambia a "pagado". |
| **Día 4 (Viernes 25)** | Grabación del Video Demo (pantalla dividida: Llamada vs. Notion), edición del README en GitHub y entrega final antes de las 14:00 h CDMX. | Enlace de GitHub, Video Demo y proyecto enviado en el panel de hacker de Goya Hack. |

---

## 8. Alineación con los Criterios de Evaluación del Jurado

1. **Implementación Técnica:** Integración limpia entre sistemas serverless (**Modal**), conectores de voz en tiempo real (**Retell**), API de **Notion**, motor transaccional de correo (**Resend**) y la plataforma web en **Vercel**.
2. **Innovación y Creatividad:** Transforma la cobranza tradicional en una experiencia conversacional por voz fluida donde la IA actúa como agente autónomo financiero.
3. **Usabilidad e Impacto Social:** Permite a estudiantes y usuarios liquidar o registrar pagos universitarios sin contraseñas ni navegación compleja, adaptado a cualquier dispositivo.
4. **Demo Funcional y Pitch:** Permite realizar un pitch de alto impacto mostrando en pantalla dividida cómo una llamada telefónica real modifica en vivo el registro visual de Notion y concluye con la autorización en TangemPay.
