import os
import sys
from pathlib import Path
import modal
from pydantic import BaseModel
from typing import Optional
from fastapi import Request

# 1. Definición de la Aplicación en Modal e Imagen con Dependencias
app = modal.App("goyapay-voice-backend")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi>=0.115.0",
        "pydantic>=2.0.0",
        "notion-client>=2.2.0,<3.0.0",
        "resend>=2.0.0",
        "requests>=2.32.0",
        "python-dotenv>=1.0.0",
    )
)

goyapay_secret = modal.Secret.from_name("goyapay-credentials")

# 2. Modelos de Datos (Pydantic) para las herramientas de Retell
class ConsultarPagosRequest(BaseModel):
    user_phone: Optional[str] = ""

class RegistrarPagoRequest(BaseModel):
    user_phone: Optional[str] = ""
    concepto: str
    monto: float
    usuario_nombre: Optional[str] = "Sergio Ethan Corona Hernández"

class EnviarCorreoRequest(BaseModel):
    email: Optional[str] = None
    correo: Optional[str] = None
    pago_id: Optional[str] = None
    page_id: Optional[str] = None
    concepto: str
    monto: float

@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="GET")
def health():
    return {"status": "ok", "app": "goyapay-voice-backend", "version": "1.0.0"}

# 3. Endpoint: Consultar Pagos Pendientes en Notion
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def consultar_pagos_notion(request: Request):
    import requests
    
    body = await request.json()
    args = body.get("args", body)
    
    token = os.environ.get("NOTION_API_KEY")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    user_phone = args.get("user_phone", "")
    clean_phone = "".join(filter(str.isdigit, user_phone or ""))[-10:]
    
    # Sergio Ethan usa indistintamente 7772310427 y 5669591407
    numeros_sergio = ["7772310427", "5669591407"]
    
    try:
        filter_conditions = [
            {
                "property": "Estado",
                "select": {"equals": "pendiente"}
            }
        ]
        
        if clean_phone in numeros_sergio or not clean_phone:
            # Buscar adeudos pendientes de Sergio asociados a cualquiera de sus 2 números
            phone_or = [
                {"property": "Telefono", "phone_number": {"contains": "7772310427"}},
                {"property": "Telefono", "phone_number": {"contains": "5669591407"}}
            ]
            filter_conditions.append({"or": phone_or})
        else:
            filter_conditions.append({
                "property": "Telefono",
                "phone_number": {"contains": clean_phone}
            })
            
        payload = {
            "filter": {"and": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0]
        }
        
        resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
        res_data = resp.json()
        
        results = res_data.get("results", [])
        if not results:
            return {"has_payments": False, "message": "No se encontraron pagos pendientes."}
        
        pagos = []
        texto_resumen = []
        for idx, page in enumerate(results, start=1):
            page_id = page["id"]
            props = page["properties"]
            
            concepto_items = props.get("Concepto", {}).get("title", [])
            concepto = concepto_items[0]["text"]["content"] if concepto_items else "Sin concepto"
            monto = props.get("Monto", {}).get("number", 0.0)
            
            pago_obj = {
                "numero": idx,
                "pago_id": page_id,
                "concepto": concepto,
                "monto": monto,
                "descripcion": f"{idx}. {concepto} por ${monto:.2f} pesos"
            }
            pagos.append(pago_obj)
            texto_resumen.append(f"Número {idx}: {concepto} por ${monto:.2f} pesos")
            
        return {
            "has_payments": True,
            "total_pendientes": len(pagos),
            "resumen": ", ".join(texto_resumen),
            "pagos": pagos,
            "primer_pago": pagos[0],
            "pago_id": pagos[0]["pago_id"],
            "concepto": pagos[0]["concepto"],
            "monto": pagos[0]["monto"]
        }
    except Exception as e:
        return {"has_payments": False, "error": str(e)}

# 4. Endpoint: Registrar Nuevo Pago/Gasto en Notion
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def registrar_pago_notion(request: Request):
    import requests
    
    body = await request.json()
    args = body.get("args", body)
    
    token = os.environ.get("NOTION_API_KEY")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    concepto = args.get("concepto", "Pago Universidad")
    monto = float(args.get("monto", 0.0))
    user_phone = args.get("user_phone", "")
    usuario_nombre = args.get("usuario_nombre", "Sergio Ethan Corona Hernández")
    
    clean_phone = "".join(filter(str.isdigit, user_phone or ""))[-10:]
    if clean_phone and not clean_phone.startswith("+"):
        formatted_phone = f"+52{clean_phone}"
    else:
        formatted_phone = "+527772310427"
        
    try:
        new_page_payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Concepto": {
                    "title": [{"text": {"content": concepto}}]
                },
                "Telefono": {
                    "phone_number": formatted_phone
                },
                "Usuario": {
                    "rich_text": [{"text": {"content": usuario_nombre}}]
                },
                "Monto": {
                    "number": monto
                },
                "Estado": {
                    "select": {"name": "pendiente"}
                },
                "Correo": {
                    "email": "coronahernandezs931@gmail.com"
                }
            }
        }
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=new_page_payload)
        res_data = resp.json()
        
        if resp.status_code == 200:
            return {"status": "success", "page_id": res_data["id"], "message": "Pago registrado en Notion exitosamente."}
        else:
            return {"status": "error", "error": res_data.get("message", "Error al crear página en Notion")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def generar_html_correo_tangem(concepto: str, monto: float, checkout_url: str, nombre_usuario: str = "Sergio Ethan Corona Hernández") -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoyaPay AI - Solicitud de Pago</title>
</head>
<body style="margin: 0; padding: 0; background-color: #07090e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #f8fafc;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #07090e; padding: 40px 15px;">
        <tr>
            <td align="center">
                <!-- Tarjeta Principal -->
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 540px; background: linear-gradient(180deg, #111827 0%, #0b0f19 100%); border: 1px solid #1f293d; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);">
                    
                    <!-- Header con Banner e Identidad -->
                    <tr>
                        <td style="padding: 36px 36px 24px 36px; text-align: center; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: radial-gradient(circle at 50% 0%, rgba(37, 99, 235, 0.18), transparent 70%);">
                            <div style="display: inline-block; padding: 6px 14px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 9999px; margin-bottom: 16px;">
                                <span style="color: #60a5fa; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;">✦ GOYAPAY AI &bull; TANGEM TRACK</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">Orden de Liquidación Segura</h1>
                            <p style="margin: 8px 0 0 0; color: #94a3b8; font-size: 13px;">Asistente de Voz &amp; Pasarela Web3 con Cold Wallet</p>
                        </td>
                    </tr>

                    <!-- Cuerpo del Mensaje -->
                    <tr>
                        <td style="padding: 32px 36px;">
                            <p style="margin: 0 0 20px 0; color: #cbd5e1; font-size: 15px; line-height: 1.6;">
                                Hola <strong style="color: #ffffff;">{nombre_usuario}</strong>,
                            </p>
                            <p style="margin: 0 0 24px 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                                Se ha generado tu enlace seguro de pago para liquidar el siguiente trámite académico registrado en tu cuenta de la UNAM:
                            </p>

                            <!-- Cuadro de Detalle del Concepto y Monto -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0d1322; border: 1px solid #1e293b; border-radius: 18px; margin-bottom: 28px; overflow: hidden;">
                                <tr>
                                    <td style="padding: 22px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                                        <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">Concepto a Pagar</div>
                                        <div style="font-size: 17px; font-weight: 700; color: #f1f5f9;">{concepto}</div>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 20px 24px; background: rgba(30, 41, 59, 0.4);">
                                        <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td>
                                                    <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Total a Liquidar</div>
                                                    <div style="font-size: 28px; font-weight: 800; color: #38bdf8; letter-spacing: -0.5px;">${monto:.2f} <span style="font-size: 14px; font-weight: 600; color: #94a3b8;">MXN</span></div>
                                                </td>
                                                <td align="right">
                                                    <div style="display: inline-block; padding: 6px 12px; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 10px; text-align: center;">
                                                        <span style="font-size: 11px; font-weight: 700; color: #34d399;">Pendiente</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Botón Principal TangemPay -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td align="center">
                                        <a href="{checkout_url}" target="_blank" style="display: block; width: 85%; padding: 16px 24px; background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); color: #ffffff; text-decoration: none; border-radius: 14px; font-size: 15px; font-weight: 700; text-align: center; box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.5); letter-spacing: 0.3px;">
                                            💳 Autorizar con Tangem Cold Wallet &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Info de Seguridad -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background: rgba(255, 255, 255, 0.02); border: 1px dashed rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
                                <tr>
                                    <td style="font-size: 12px; color: #94a3b8; line-height: 1.5;">
                                        🔒 <strong>Protección Criptográfica:</strong> Al pulsar el botón, tu tarjeta física Tangem validará y firmará la transacción mediante chip NFC EAL6+, actualizando automáticamente tu adeudo en Notion.
                                    </td>
                                </tr>
                            </table>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 36px 30px 36px; background-color: #090d16; border-top: 1px solid rgba(255, 255, 255, 0.05); text-align: center;">
                            <p style="margin: 0 0 6px 0; color: #64748b; font-size: 12px; font-weight: 500;">
                                GoyaPay AI &bull; Proyecto Oficial Goya Hack 2026
                            </p>
                            <p style="margin: 0; color: #475569; font-size: 11px;">
                                Si no solicitaste este enlace, puedes ignorar este correo con total tranquilidad.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

# 5. Endpoint: Enviar Correo con Resend
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def enviar_correo_pago(request: Request):
    import resend
    import urllib.parse
    
    body = await request.json()
    args = body.get("args", body)
    
    resend.api_key = os.environ.get("RESEND_API_KEY")
    base_checkout_url = os.environ.get("VERCEL_CHECKOUT_URL", "https://checkout-web-seven.vercel.app/checkout")
    
    resolved_page_id = args.get("pago_id") or args.get("page_id") or ""
    resolved_email = args.get("correo") or args.get("email") or "coronahernandezs931@gmail.com"
    concepto = args.get("concepto", "Credencial de Biblioteca")
    try:
        monto = float(args.get("monto", 120.0))
    except (ValueError, TypeError):
        monto = 120.0
    
    params = urllib.parse.urlencode({
        "page_id": resolved_page_id,
        "monto": str(monto),
        "concepto": concepto,
        "email": resolved_email
    })
    checkout_url = f"{base_checkout_url}?{params}"
    
    html_template = generar_html_correo_tangem(concepto=concepto, monto=monto, checkout_url=checkout_url)
    
    try:
        response = resend.Emails.send({
            "from": "GoyaPay AI <onboarding@resend.dev>",
            "to": [resolved_email],
            "subject": f"GoyaPay: Enlace de Autorización para {concepto}",
            "html": html_template
        })
        return {"status": "success", "email_id": response.get("id"), "checkout_url": checkout_url}
    except Exception as e:
        return {"status": "error", "message": "error al enviar correo", "detail": str(e)}

# 6. Endpoint: Confirmar Pago desde Checkout (Actualiza Estado a 'pagado' en Notion y Envía Recibo de Agradecimiento)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def confirmar_pago_notion(request: Request):
    import requests
    import resend
    
    body = await request.json()
    args = body.get("args", body)
    
    token = os.environ.get("NOTION_API_KEY")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    page_id = args.get("page_id") or args.get("pago_id") or ""
    wallet_address = args.get("wallet_address", "0x92932D7d5341B84f524D0715F3cac55C10d12E4e")
    user_email = args.get("email") or "coronahernandezs931@gmail.com"
    concepto = args.get("concepto", "Trámite UNAM")
    monto = args.get("monto", "0.00")
    
    payload = {
        "properties": {
            "Estado": {
                "select": {"name": "pagado"}
            }
        }
    }
    
    try:
        resp = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json=payload)
        res_data = resp.json()
        
        # Enviar correo de confirmación y agradecimiento
        try:
            resend.api_key = os.environ.get("RESEND_API_KEY")
            correo_agradecimiento = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; background-color: #07090e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 40px 15px;">
        <tr>
            <td align="center">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 540px; background: linear-gradient(180deg, #111827 0%, #0b0f19 100%); border: 1px solid #10b981; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.7);">
                    <tr>
                        <td style="padding: 36px 36px 20px 36px; text-align: center; background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.2), transparent 70%);">
                            <div style="display: inline-block; width: 56px; height: 56px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); border: 2px solid #10b981; line-height: 56px; font-size: 26px; margin-bottom: 14px;">
                                ✅
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800;">¡Gracias por usar GoyaPay AI!</h1>
                            <p style="margin: 6px 0 0 0; color: #34d399; font-size: 14px; font-weight: 600;">Comprobante de Pago Liquidado Exitosamente</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 24px 36px 32px 36px;">
                            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                                Hola <strong>Sergio Ethan Corona Hernández</strong>, tu transacción con <strong>Tangem Cold Wallet</strong> ha sido autenticada y registrada en el sistema de la UNAM.
                            </p>
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0d1322; border: 1px solid #1e293b; border-radius: 16px; margin-bottom: 20px; padding: 18px 20px;">
                                <tr>
                                    <td style="padding-bottom: 10px; color: #94a3b8; font-size: 12px;">Concepto:</td>
                                    <td align="right" style="padding-bottom: 10px; color: #ffffff; font-weight: 700; font-size: 13px;">{concepto}</td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 10px; color: #94a3b8; font-size: 12px;">Monto Liquidado:</td>
                                    <td align="right" style="padding-bottom: 10px; color: #34d399; font-weight: 800; font-size: 16px;">${float(monto):.2f} MXN</td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 10px; color: #94a3b8; font-size: 12px;">Wallet Hardware:</td>
                                    <td align="right" style="padding-bottom: 10px; color: #60a5fa; font-family: monospace; font-size: 11px;">{wallet_address[:8]}...{wallet_address[-6:]}</td>
                                </tr>
                                <tr>
                                    <td style="color: #94a3b8; font-size: 12px;">Estado Notion:</td>
                                    <td align="right" style="color: #34d399; font-weight: 700; font-size: 12px;">PAGADO (Actualizado)</td>
                                </tr>
                            </table>
                            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">
                                ¡Mucho éxito en tu presentación de Goya Hack 2026! 🚀
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
            resend.Emails.send({
                "from": "GoyaPay AI <onboarding@resend.dev>",
                "to": [user_email],
                "subject": f"✅ Comprobante de Pago Exitoso: {concepto} (GoyaPay Tangem)",
                "html": correo_agradecimiento
            })
        except Exception as err_mail:
            print("Error enviando recibo de agradecimiento:", err_mail)
            
        if resp.status_code == 200:
            return {"status": "success", "page_id": page_id, "estado": "pagado"}
        else:
            return {"status": "error", "message": res_data.get("message", "Error al actualizar Notion")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 7. Endpoint: Chat Asistente de Texto (Sofía Web Chat)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def chat_goyapay(request: Request):
    import requests
    
    body = await request.json()
    mensaje = body.get("mensaje", "").strip().lower()
    user_phone = body.get("user_phone", "7772310427")
    user_email = body.get("user_email", "coronahernandezs931@gmail.com")
    
    # 1. Consultar Notion
    db_id = os.environ.get("NOTION_DATABASE_ID")
    token = os.environ.get("NOTION_API_KEY")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        query_payload = {
            "filter": {
                "and": [
                    {"property": "Estado", "select": {"equals": "pendiente"}},
                    {"or": [
                        {"property": "Telefono", "phone_number": {"contains": "7772310427"}},
                        {"property": "Telefono", "phone_number": {"contains": "5669591407"}}
                    ]}
                ]
            }
        }
        resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=query_payload)
        res_data = resp.json()
        results = res_data.get("results", [])
        
        pagos = []
        for idx, page in enumerate(results, start=1):
            p_id = page["id"]
            props = page["properties"]
            t_items = props.get("Concepto", {}).get("title", [])
            c_text = t_items[0]["text"]["content"] if t_items else "Sin concepto"
            m_val = props.get("Monto", {}).get("number", 0.0)
            pagos.append({"numero": idx, "pago_id": p_id, "concepto": c_text, "monto": m_val})
        
        # Lógica de detección de intención del mensaje
        if any(w in mensaje for w in ["pago", "adeudo", "debo", "deuda", "pendiente", "consultar", "saldo", "hola"]):
            if not pagos:
                return {
                    "respuesta": "¡Hola Sergio! He consultado el sistema y no tienes ningún adeudo pendiente en este momento. Estás totalmente al corriente.",
                    "pagos": []
                }
            
            resumen_lineas = [f"{p['numero']}. {p['concepto']} por ${p['monto']:.2f} MXN" for p in pagos]
            texto_resp = (
                f"¡Hola Sergio! Tienes {len(pagos)} adeudo(s) pendiente(s):\n\n" +
                "\n".join(resumen_lineas) +
                "\n\n¿Cuál de ellos deseas pagar? Puedes responder con el número (ej: 'pagar el 1') o hacer clic en el botón de liquidación."
            )
            return {"respuesta": texto_resp, "pagos": pagos}
            
        elif any(w in mensaje for w in ["1", "primero", "2", "segundo", "3", "tercero", "4", "cuarto", "pagar", "liquidar"]):
            # Identificar qué pago seleccionó
            seleccion = None
            if "1" in mensaje or "primer" in mensaje:
                seleccion = pagos[0] if len(pagos) >= 1 else None
            elif "2" in mensaje or "segund" in mensaje:
                seleccion = pagos[1] if len(pagos) >= 2 else None
            elif "3" in mensaje or "tercer" in mensaje:
                seleccion = pagos[2] if len(pagos) >= 3 else None
            elif "4" in mensaje or "cuart" in mensaje:
                seleccion = pagos[3] if len(pagos) >= 4 else None
            elif pagos:
                seleccion = pagos[0]
            
            if seleccion:
                # Disparar envío de correo
                import urllib.parse
                base_url = os.environ.get("VERCEL_CHECKOUT_URL", "https://checkout-web-seven.vercel.app/checkout")
                params = urllib.parse.urlencode({
                    "page_id": seleccion["pago_id"],
                    "monto": str(seleccion["monto"]),
                    "concepto": seleccion["concepto"],
                    "email": user_email
                })
                checkout_url = f"{base_url}?{params}"
                
                # Enviar correo vía Resend
                try:
                    import resend
                    resend.api_key = os.environ.get("RESEND_API_KEY")
                    html_chat_email = generar_html_correo_tangem(
                        concepto=seleccion['concepto'],
                        monto=float(seleccion['monto']),
                        checkout_url=checkout_url
                    )
                    resend.Emails.send({
                        "from": "GoyaPay AI <onboarding@resend.dev>",
                        "to": [user_email],
                        "subject": f"GoyaPay: Enlace de Autorización para {seleccion['concepto']}",
                        "html": html_chat_email
                    })
                except Exception as ex_mail:
                    print("Error enviando correo en chat:", ex_mail)
                
                return {
                    "respuesta": f"¡Excelente! Te he enviado el enlace seguro de pago para {seleccion['concepto']} (${seleccion['monto']:.2f} MXN) a tu correo registrado ({user_email}). También puedes abrirlo directamente aquí abajo:",
                    "checkout_url": checkout_url,
                    "pago_seleccionado": seleccion
                }
            else:
                return {
                    "respuesta": "No encontré ese adeudo en la lista. Si deseas ver tus adeudos pendientes, escribe 'ver adeudos'."
                }
        else:
            return {
                "respuesta": "Soy Sofía de GoyaPay AI. Puedes escribirme 'consultar adeudos' para ver tu lista de pagos pendientes o 'pagar el 1' para recibir tu enlace de TangemPay."
            }
    except Exception as e:
        return {"respuesta": f"Hubo un detalle al consultar Notion: {str(e)}", "error": str(e)}

