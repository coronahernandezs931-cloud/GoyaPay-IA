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
        "stripe>=7.0.0",
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

                            <!-- Botones Principales: Tangem & Stripe -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td align="center" style="padding-bottom: 12px;">
                                        <a href="{checkout_url}&metodo=tangem" target="_blank" style="display: block; width: 85%; padding: 15px 20px; background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); color: #ffffff; text-decoration: none; border-radius: 14px; font-size: 14px; font-weight: 700; text-align: center; box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.4); letter-spacing: 0.3px;">
                                            🔐 Conectar Tangem Cold Wallet (NFC) &rarr;
                                        </a>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center">
                                        <a href="{checkout_url}&metodo=tarjeta" target="_blank" style="display: block; width: 85%; padding: 15px 20px; background: linear-gradient(135deg, #059669 0%, #0d9488 100%); color: #ffffff; text-decoration: none; border-radius: 14px; font-size: 14px; font-weight: 700; text-align: center; box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.4); letter-spacing: 0.3px;">
                                            💳 Pagar Directo con Stripe (Tarjeta) &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Info de Métodos -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background: rgba(255, 255, 255, 0.02); border: 1px dashed rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
                                <tr>
                                    <td style="font-size: 12px; color: #94a3b8; line-height: 1.5;">
                                        ⚡ <strong>Elige tu método favorito:</strong> Puedes autorizar con hardware criptográfico <b>Tangem NFC</b>, pagar directo en la pasarela oficial de <b>Stripe Checkout</b> (Visa, Mastercard, AMEX, Apple Pay) o realizar transferencia <b>SPEI</b>. Tu estado en Notion se liquidará de inmediato.
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

# 6. Generador de Comprobantes de Pago Multibanco (Avalanche, Tangem, Pollar, SPEI, Tarjeta)
def generar_html_correo_recibo(concepto: str, monto: float, metodo_pago: str, detalle: str, nombre_usuario: str = "Sergio Ethan Corona Hernández") -> str:
    metodo_lower = metodo_pago.lower()
    es_spei = "spei" in metodo_lower
    es_tarjeta = "tarjeta" in metodo_lower or "stripe" in metodo_lower
    es_pollar = "pollar" in metodo_lower or "stellar" in metodo_lower
    
    if es_pollar:
        badge_txt = "POLLAR SMART WALLET • RED STELLAR"
        badge_bg = "rgba(16, 185, 129, 0.15)"
        badge_border = "rgba(16, 185, 129, 0.3)"
        badge_color = "#34d399"
        subtitulo = "Liquidación Descentralizada Validada en Stellar Testnet"
        detalle_lbl = "Pollar Wallet / Stellar Tx:"
        detalle_val = detalle if detalle else "GBHMU52LYYDXE7HGVEEFGQOKM3UZEAHUSLH6TRPVGWACBQM6BAVUBTM7"
        icono = "🪙"
    elif es_spei:
        badge_txt = "TRANSFERENCIA SPEI ACREDITADA"
        badge_bg = "rgba(16, 185, 129, 0.15)"
        badge_border = "rgba(16, 185, 129, 0.3)"
        badge_color = "#34d399"
        subtitulo = "Comprobante de Transferencia Interbancaria en STP"
        detalle_lbl = "Folio / Banco:"
        detalle_val = detalle if detalle else "STP • CLABE 646180123456789012"
        icono = "🏦"
    elif es_tarjeta:
        badge_txt = "COBRO BANCARIO 3D-SECURE"
        badge_bg = "rgba(59, 130, 246, 0.15)"
        badge_border = "rgba(59, 130, 246, 0.3)"
        badge_color = "#60a5fa"
        subtitulo = "Comprobante de Autorización Bancaria Segura"
        detalle_lbl = "Método / Tarjeta:"
        detalle_val = detalle if detalle else "Tarjeta Débito/Crédito Cifrada"
        icono = "💳"
    else:
        badge_txt = "AVALANCHE C-CHAIN • TANGEM NFC COLD WALLET"
        badge_bg = "rgba(229, 62, 62, 0.15)"
        badge_border = "rgba(229, 62, 62, 0.3)"
        badge_color = "#fc8181"
        subtitulo = "Transacción On-Chain Avalanche C-Chain Validada con Hardware EAL6+"
        detalle_lbl = "Hash Avalanche / Snowtrace:"
        detalle_val = detalle if detalle else "0x7f9a2b84c01d93e1572bc468d02e482390f142bc (Snowtrace)"
        icono = "❄️"

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; background-color: #07090e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 40px 15px;">
        <tr>
            <td align="center">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 540px; background: linear-gradient(180deg, #111827 0%, #0b0f19 100%); border: 1px solid #1e293b; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.7);">
                    <tr>
                        <td style="padding: 36px 36px 20px 36px; text-align: center; background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.18), transparent 70%);">
                            <div style="display: inline-block; padding: 6px 14px; background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 9999px; margin-bottom: 14px;">
                                <span style="color: {badge_color}; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">{badge_txt}</span>
                            </div>
                            <div style="font-size: 32px; margin-bottom: 8px;">{icono}</div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800;">¡Gracias por usar GoyaPay AI!</h1>
                            <p style="margin: 6px 0 0 0; color: #34d399; font-size: 14px; font-weight: 600;">{subtitulo}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 24px 36px 32px 36px;">
                            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                                Hola <strong style="color: #ffffff;">{nombre_usuario}</strong>, tu transacción ha sido confirmada y registrada en el sistema de gestión del negocio y la UNAM.
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
                                    <td style="padding-bottom: 10px; color: #94a3b8; font-size: 12px;">{detalle_lbl}</td>
                                    <td align="right" style="padding-bottom: 10px; color: #60a5fa; font-family: monospace; font-size: 11px;">{detalle_val}</td>
                                </tr>
                                <tr>
                                    <td style="color: #94a3b8; font-size: 12px;">Estado en Sistema:</td>
                                    <td align="right" style="color: #34d399; font-weight: 700; font-size: 12px;">PAGADO (Sincronizado)</td>
                                </tr>
                            </table>
                            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">
                                GoyaPay Business Manager • Plataforma Oficial de Liquidación Multibanco & Web3 🚀
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

# 7. Endpoint: Confirmar Pago desde Checkout (Multibanco: Tangem, SPEI, Tarjeta)
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
    metodo_pago = args.get("metodo_pago") or args.get("metodo") or "Tangem Cold Wallet NFC"
    detalle = args.get("detalle") or args.get("wallet_address") or "0x92932D7d5341B84f524D0715F3cac55C10d12E4e"
    user_email = args.get("email") or "coronahernandezs931@gmail.com"
    concepto = args.get("concepto", "Trámite / Servicio")
    try:
        monto = float(args.get("monto", 0.0))
    except (ValueError, TypeError):
        monto = 0.0
    
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
        
        # Enviar correo de comprobante adaptado al método de pago
        try:
            resend.api_key = os.environ.get("RESEND_API_KEY")
            correo_agradecimiento = generar_html_correo_recibo(
                concepto=concepto,
                monto=monto,
                metodo_pago=metodo_pago,
                detalle=detalle,
                nombre_usuario="Sergio Ethan Corona Hernández"
            )
            resend.Emails.send({
                "from": "GoyaPay AI <onboarding@resend.dev>",
                "to": [user_email],
                "subject": f"✅ Comprobante de Pago Exitoso: {concepto} ({metodo_pago})",
                "html": correo_agradecimiento
            })
        except Exception as err_mail:
            print("Error enviando recibo de agradecimiento:", err_mail)
            
        if resp.status_code == 200:
            return {
                "status": "success",
                "page_id": page_id,
                "estado": "pagado",
                "metodo_pago": metodo_pago,
                "detalle": detalle
            }
        else:
            return {"status": "error", "message": res_data.get("message", "Error al actualizar Notion")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================================================================
# 8. MÓDULO DE ADMINISTRACIÓN DE NEGOCIO: FINANZAS (NOTION) & CUENTAS (ZERNIO API)
# ==============================================================================
def obtener_analisis_finanzas_negocio(db_id: str, token: str) -> dict:
    import requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json={})
    data = resp.json()
    results = data.get("results", [])
    
    total_cobrado = 0.0
    total_pendiente = 0.0
    pagados = []
    pendientes = []
    
    for page in results:
        props = page.get("properties", {})
        title_items = props.get("Concepto", {}).get("title", [])
        concepto = title_items[0]["text"]["content"] if title_items else "Sin concepto"
        monto = float(props.get("Monto", {}).get("number", 0.0) or 0.0)
        estado_obj = props.get("Estado", {}).get("select") or {}
        estado = estado_obj.get("name", "pendiente")
        
        item = {
            "id": page.get("id"),
            "concepto": concepto,
            "monto": monto,
            "estado": estado
        }
        
        if estado == "pagado":
            total_cobrado += monto
            pagados.append(item)
        else:
            total_pendiente += monto
            pendientes.append(item)
            
    balance_neto = total_cobrado - total_pendiente
    total_transacciones = len(results)
    tasa_cobranza = (total_cobrado / (total_cobrado + total_pendiente) * 100) if (total_cobrado + total_pendiente) > 0 else 100.0
    ticket_promedio = (total_cobrado / len(pagados)) if pagados else 0.0
    
    if total_pendiente == 0:
        salud = "Excelente"
        diagnostico = f"El negocio cuenta con un 100% de cobranza efectiva. Se han liquidado {len(pagados)} transacciones recaudando ${total_cobrado:.2f} MXN sin adeudos pendientes."
    elif balance_neto > 0:
        salud = "Saludable"
        diagnostico = f"Flujo neto positivo de +${balance_neto:.2f} MXN. Se han cobrado ${total_cobrado:.2f} MXN con ${total_pendiente:.2f} MXN en cuentas por cobrar ({tasa_cobranza:.1f}% tasa de cobranza)."
    else:
        salud = "Atención requerida"
        diagnostico = f"Los gastos/adeudos pendientes (${total_pendiente:.2f} MXN) superan los ingresos recaudados (${total_cobrado:.2f} MXN). Se recomienda activar cobranza asistida."
        
    return {
        "salud_financiera": salud,
        "total_cobrado": total_cobrado,
        "total_pendiente": total_pendiente,
        "balance_neto": balance_neto,
        "tasa_cobranza_pct": round(tasa_cobranza, 1),
        "total_transacciones": total_transacciones,
        "ticket_promedio": round(ticket_promedio, 2),
        "diagnostico": diagnostico,
        "num_pagados": len(pagados),
        "num_pendientes": len(pendientes),
        "pagados_recientes": pagados[:5],
        "pendientes_recientes": pendientes[:5]
    }

def obtener_analisis_zernio(api_key: str) -> dict:
    import requests
    headers = {"Authorization": f"Bearer {(api_key or '').strip()}"}
    
    # 1. Cuentas conectadas
    r_acc = requests.get("https://zernio.com/api/v1/accounts", headers=headers)
    accounts = r_acc.json().get("accounts", []) if r_acc.status_code == 200 else []
    
    canales = []
    total_seguidores = 0
    for a in accounts:
        followers = a.get("followersCount", 0) or 0
        total_seguidores += followers
        canales.append({
            "plataforma": a.get("platform"),
            "display_name": a.get("displayName"),
            "username": a.get("username"),
            "seguidores": followers,
            "activo": a.get("isActive", True),
            "profile_url": a.get("profileUrl") or a.get("metadata", {}).get("profileUrl")
        })
        
    # 2. Analíticas de publicaciones
    r_an = requests.get("https://zernio.com/api/v1/analytics", headers=headers)
    an_data = r_an.json() if r_an.status_code == 200 else {}
    posts_an = an_data.get("posts", an_data.get("results", []))
    
    total_vistas = 0
    total_likes = 0
    total_shares = 0
    total_comments = 0
    sum_engagement = 0.0
    posts_con_eng = 0
    
    for p in posts_an:
        if isinstance(p, dict):
            an = p.get("analytics", {})
            vistas = an.get("views", 0) or 0
            likes = an.get("likes", 0) or 0
            shares = an.get("shares", 0) or 0
            comments = an.get("comments", 0) or 0
            eng = an.get("engagementRate", 0.0) or 0.0
            
            total_vistas += vistas
            total_likes += likes
            total_shares += shares
            total_comments += comments
            if eng > 0:
                sum_engagement += eng
                posts_con_eng += 1
                
    engagement_promedio = (sum_engagement / posts_con_eng) if posts_con_eng > 0 else 0.0
    
    # 3. Posts programados en pipeline
    r_posts = requests.get("https://zernio.com/api/v1/posts", headers=headers)
    posts_data = r_posts.json() if r_posts.status_code == 200 else {}
    total_posts_pipeline = posts_data.get("pagination", {}).get("total", 0)
    
    diagnostico_audiencia = (
        f"Tu negocio tiene presencia activa en {len(canales)} canales (TikTok y YouTube), "
        f"con {total_seguidores} seguidores y más de {total_vistas:,} visualizaciones orgánicas acumuladas en {len(posts_an)} publicaciones. "
        f"Tasa de interacción promedio del {engagement_promedio:.2f}%. Tienes un pipeline constante con {total_posts_pipeline} publicaciones programadas en cola."
    )
    
    return {
        "canales_activos": canales,
        "total_canales": len(canales),
        "total_seguidores": total_seguidores,
        "total_vistas": total_vistas,
        "total_likes": total_likes,
        "total_shares": total_shares,
        "total_comments": total_comments,
        "engagement_promedio_pct": round(engagement_promedio, 2),
        "posts_en_pipeline": total_posts_pipeline,
        "posts_analizados": len(posts_an),
        "diagnostico_audiencia": diagnostico_audiencia
    }

# 9. Endpoint: Analizar Finanzas y Gastos del Negocio (Notion CRM)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def analizar_finanzas_negocio(request: Request):
    token = os.environ.get("NOTION_API_KEY")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    try:
        analisis = obtener_analisis_finanzas_negocio(db_id, token)
        return {"status": "success", "analisis": analisis}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 10. Endpoint: Analizar Cuentas Digitales y Audiencia del Negocio (Zernio API)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def analizar_cuentas_negocio(request: Request):
    zernio_key = os.environ.get("ZERNIO_API_KEY", "")
    try:
        analisis = obtener_analisis_zernio(zernio_key)
        return {"status": "success", "analisis": analisis}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 11. Endpoint: Resumen Ejecutivo 360° del Negocio (Finanzas + Cuentas Zernio)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def resumen_administrador_negocio(request: Request):
    token = os.environ.get("NOTION_API_KEY")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    zernio_key = os.environ.get("ZERNIO_API_KEY", "")
    
    try:
        finanzas = obtener_analisis_finanzas_negocio(db_id, token)
    except Exception as e:
        finanzas = {"error": str(e)}
        
    try:
        cuentas = obtener_analisis_zernio(zernio_key)
    except Exception as e:
        cuentas = {"error": str(e)}
        
    return {
        "status": "success",
        "administrador": "Sergio Ethan Corona Hernández",
        "plataforma": "GoyaPay Business Manager",
        "finanzas": finanzas,
        "cuentas_digitales": cuentas,
        "resumen_ejecutivo": f"💼 **Reporte Ejecutivo GoyaPay Negocios**:\n"
                            f"• Total Recaudado: ${finanzas.get('total_cobrado', 0.0):.2f} MXN ({finanzas.get('num_pagados', 0)} transacciones)\n"
                            f"• Adeudos/Gastos Pendientes: ${finanzas.get('total_pendiente', 0.0):.2f} MXN\n"
                            f"• Balance Neto Operativo: +${finanzas.get('balance_neto', 0.0):.2f} MXN (Salud: {finanzas.get('salud_financiera', 'N/A')})\n"
                            f"• Cuentas Conectadas en Zernio: {cuentas.get('total_canales', 0)} ({cuentas.get('total_seguidores', 0)} seguidores totales)\n"
                            f"• Alcance de Contenidos: {cuentas.get('total_vistas', 0):,} vistas acumuladas con {cuentas.get('total_likes', 0)} likes\n"
                            f"• Pipeline de Publicaciones: {cuentas.get('posts_en_pipeline', 0)} publicaciones programadas"
    }

# 12. Endpoint: Registrar Gasto o Cuenta del Negocio en Notion
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def registrar_gasto_negocio(request: Request):
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
    
    concepto = args.get("concepto", "Gasto Operativo Negocio")
    monto = float(args.get("monto", 0.0))
    estado = args.get("estado", "pendiente")
    telefono = args.get("telefono", "+527772310427")
    usuario = args.get("usuario", "GoyaPay Negocios / Sergio Ethan")
    email = args.get("email", "coronahernandezs931@gmail.com")
    
    try:
        new_page_payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Concepto": {
                    "title": [{"text": {"content": concepto}}]
                },
                "Telefono": {
                    "phone_number": telefono
                },
                "Usuario": {
                    "rich_text": [{"text": {"content": usuario}}]
                },
                "Monto": {
                    "number": monto
                },
                "Estado": {
                    "select": {"name": estado}
                },
                "Correo": {
                    "email": email
                }
            }
        }
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=new_page_payload)
        res_data = resp.json()
        if resp.status_code == 200:
            return {"status": "success", "page_id": res_data["id"], "concepto": concepto, "monto": monto, "estado": estado}
        else:
            return {"status": "error", "error": res_data.get("message", "Error al registrar en Notion")}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 13. Endpoint: Chat Asistente de Texto (Sofía Web Chat & Business Manager)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def chat_goyapay(request: Request):
    import requests
    
    body = await request.json()
    mensaje = body.get("mensaje", "").strip().lower()
    user_phone = body.get("user_phone", "7772310427")
    user_email = body.get("user_email", "coronahernandezs931@gmail.com")
    
    db_id = os.environ.get("NOTION_DATABASE_ID")
    token = os.environ.get("NOTION_API_KEY")
    zernio_key = os.environ.get("ZERNIO_API_KEY", "")
    
    # Intención: Análisis de Finanzas / Gastos del Negocio
    if any(w in mensaje for w in ["finanza", "gasto", "balance", "ingreso", "flujo", "caja", "cuentas de mi negocio"]):
        try:
            fin = obtener_analisis_finanzas_negocio(db_id, token)
            texto_resp = (
                f"💼 **Diagnóstico Financiero de tu Negocio:**\n\n"
                f"• **Ingresos Recaudados:** ${fin['total_cobrado']:.2f} MXN ({fin['num_pagados']} cobros liquidados)\n"
                f"• **Gastos / Adeudos Pendientes:** ${fin['total_pendiente']:.2f} MXN ({fin['num_pendientes']} pendientes)\n"
                f"• **Balance Neto:** +${fin['balance_neto']:.2f} MXN\n"
                f"• **Efectividad de Cobranza:** {fin['tasa_cobranza_pct']}%\n"
                f"• **Ticket Promedio:** ${fin['ticket_promedio']:.2f} MXN\n\n"
                f"📊 **Evaluación de Salud:** *{fin['salud_financiera']}*\n{fin['diagnostico']}"
            )
            return {"respuesta": texto_resp, "analisis_finanzas": fin}
        except Exception as e:
            return {"respuesta": f"Detalle al analizar finanzas: {str(e)}", "error": str(e)}

    # Intención: Programar Video en Redes (Zernio API)
    elif any(w in mensaje for w in ["programar video", "subir video", "publicar video", "programar publicación", "subir a tiktok", "subir a youtube", "programar tiktok", "programar youtube"]):
        texto_resp = (
            f"🎬 **Programador de Videos en Redes Sociales (Zernio API):**\n\n"
            f"¡Puedes programar y publicar videos directamente en tus canales de TikTok (@flutter.py) y YouTube (@sergioethancoronahernandez)!\n\n"
            f"1. Abre el modal pulsando el botón **'🎬 Programar Video'** en la barra de acciones superior de GoyaPay.\n"
            f"2. Ingresa el título del video, su descripción con hashtags y la URL del archivo de video.\n"
            f"3. Selecciona si deseas publicación inmediata o programada para una fecha y hora específica.\n\n"
            f"🔗 [Acceder al Panel de Zernio](https://zernio.com/dashboard)"
        )
        return {"respuesta": texto_resp, "dashboard_url": "https://zernio.com/dashboard", "abrir_modal_video": True}

    # Intención: Enlace directo al Panel de Zernio
    elif any(w in mensaje for w in ["panel de zernio", "link de zernio", "abrir zernio", "dashboard zernio", "ver zernio", "entrar a zernio"]):
        texto_resp = (
            f"🌐 **Panel Oficial de Zernio:**\n\n"
            f"Puedes acceder directamente a tu panel de control para gestionar publicaciones, auditar canales y revisar métricas detalladas en el siguiente enlace:\n\n"
            f"👉 [Abrir Panel de Zernio](https://zernio.com/dashboard)\n\n"
            f"*(También puedes pulsar el botón 'Ver Panel de Zernio ↗' en tu panel de GoyaPay)*."
        )
        return {"respuesta": texto_resp, "dashboard_url": "https://zernio.com/dashboard"}

    # Intención: Análisis de Cuentas Digitales y Contenidos (Zernio API)
    elif any(w in mensaje for w in ["red", "redes", "canal", "tiktok", "youtube", "zernio", "audiencia", "seguidor", "metricas", "vistas", "pipeline"]):
        try:
            zer = obtener_analisis_zernio(zernio_key)
            canales_txt = ", ".join([f"{c['plataforma'].capitalize()} (@{c['username']} - {c['seguidores']} seguidores)" for c in zer['canales_activos']])
            texto_resp = (
                f"🌐 **Análisis de Cuentas y Canales Digitales (Vía Zernio API):**\n\n"
                f"• **Canales Conectados ({zer['total_canales']}):** {canales_txt}\n"
                f"• **Seguidores Totales:** {zer['total_seguidores']}\n"
                f"• **Visualizaciones Acumuladas:** {zer['total_vistas']:,} vistas orgánicas\n"
                f"• **Reacciones & Likes:** {zer['total_likes']} likes ({zer['total_shares']} compartidos)\n"
                f"• **Tasa de Interacción Media:** {zer['engagement_promedio_pct']}%\n"
                f"• **Pipeline Activo:** {zer['posts_en_pipeline']} publicaciones programadas en cola.\n\n"
                f"🔗 [Acceder a tu Panel de Zernio](https://zernio.com/dashboard)\n\n"
                f"🚀 **Diagnóstico:** {zer['diagnostico_audiencia']}"
            )
            return {"respuesta": texto_resp, "analisis_cuentas": zer, "dashboard_url": "https://zernio.com/dashboard"}
        except Exception as e:
            return {"respuesta": f"Detalle al consultar Zernio: {str(e)}", "error": str(e)}

    # Intención: Resumen Ejecutivo 360° del Negocio
    elif any(w in mensaje for w in ["360", "resumen", "ejecutivo", "administrador", "reporte", "como va", "panorama", "diagnostico"]):
        try:
            fin = obtener_analisis_finanzas_negocio(db_id, token)
            zer = obtener_analisis_zernio(zernio_key)
            texto_resp = (
                f"🏢 **Resumen Ejecutivo 360° - GoyaPay Business Manager**\n\n"
                f"**1. Finanzas y Cobranza (Notion CRM):**\n"
                f"• Cobrado: ${fin['total_cobrado']:.2f} MXN | Pendiente: ${fin['total_pendiente']:.2f} MXN\n"
                f"• Balance Neto: +${fin['balance_neto']:.2f} MXN (Tasa Cobranza: {fin['tasa_cobranza_pct']}%)\n\n"
                f"**2. Cuentas Digitales y Difusión (Zernio API):**\n"
                f"• Presencia en: TikTok y YouTube ({zer['total_seguidores']} seguidores)\n"
                f"• Tracción: {zer['total_vistas']:,} vistas acumuladas y {zer['posts_en_pipeline']} videos en pipeline\n\n"
                f"✅ **Veredicto:** El negocio goza de excelente solvencia financiera y un ritmo de publicación automatizado muy consistente."
            )
            return {"respuesta": texto_resp, "finanzas": fin, "cuentas": zer}
        except Exception as e:
            return {"respuesta": f"Detalle generando reporte: {str(e)}", "error": str(e)}

    # Consultar Notion para Adeudos Pendientes habituales
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
        
        if any(w in mensaje for w in ["pago", "adeudo", "debo", "deuda", "pendiente", "consultar", "saldo", "hola"]):
            if not pagos:
                return {
                    "respuesta": "¡Hola Sergio! He consultado el sistema y no tienes ningún adeudo pendiente en este momento. Estás totalmente al corriente.\n\nTambién puedo ayudarte a:\n• 💼 **Analizar finanzas del negocio**\n• 🌐 **Analizar cuentas digitales (Zernio)**\n• 🏢 **Ver resumen ejecutivo del negocio**",
                    "pagos": []
                }
            
            resumen_lineas = [f"{p['numero']}. {p['concepto']} por ${p['monto']:.2f} MXN" for p in pagos]
            texto_resp = (
                f"¡Hola Sergio! Tienes {len(pagos)} adeudo(s) pendiente(s):\n\n" +
                "\n".join(resumen_lineas) +
                "\n\n¿Cuál de ellos deseas pagar? Puedes responder 'pagar el 1' para recibir tu enlace con opción de **Tangem Cold Wallet, SPEI Banco o Tarjeta**."
            )
            return {"respuesta": texto_resp, "pagos": pagos}
            
        elif any(w in mensaje for w in ["1", "primero", "2", "segundo", "3", "tercero", "4", "cuarto", "pagar", "liquidar"]):
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
                import urllib.parse
                base_url = os.environ.get("VERCEL_CHECKOUT_URL", "https://checkout-web-seven.vercel.app/checkout")
                params = urllib.parse.urlencode({
                    "page_id": seleccion["pago_id"],
                    "monto": str(seleccion["monto"]),
                    "concepto": seleccion["concepto"],
                    "email": user_email
                })
                checkout_url = f"{base_url}?{params}"
                
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
                        "subject": f"GoyaPay: Enlace de Autorización para {seleccion['concepto']} (Multibanco & Tangem)",
                        "html": html_chat_email
                    })
                except Exception as ex_mail:
                    print("Error enviando correo en chat:", ex_mail)
                
                return {
                    "respuesta": f"¡Excelente! Te he enviado el enlace seguro de pago para {seleccion['concepto']} (${seleccion['monto']:.2f} MXN) a tu correo ({user_email}). Puedes pagar con Tangem Cold Wallet, Transferencia SPEI o Tarjeta Bancaria:",
                    "checkout_url": checkout_url,
                    "pago_seleccionado": seleccion
                }
            else:
                return {
                    "respuesta": "No encontré ese adeudo en la lista. Si deseas ver tus adeudos pendientes, escribe 'ver adeudos'."
                }
        else:
            return {
                "respuesta": "Soy Sofía de GoyaPay AI Business. Puedo ayudarte con:\n• 📋 Consultar adeudos o pagar trámites (Tangem, SPEI o Tarjeta)\n• 💼 **Analizar finanzas del negocio**\n• 🌐 **Analizar cuentas digitales (Zernio)**\n• 🏢 **Resumen ejecutivo 360° del negocio**"
            }
    except Exception as e:
        return {"respuesta": f"Hubo un detalle al procesar la solicitud: {str(e)}", "error": str(e)}

# 14. Endpoint: Crear Sesión Oficial en Stripe Checkout (Opción A)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def crear_sesion_stripe(request: Request):
    import stripe
    import urllib.parse
    
    body = await request.json()
    args = body.get("args", body)
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return {"status": "error", "message": "STRIPE_SECRET_KEY no configurada en variables de entorno"}
    
    stripe.api_key = stripe_key
    
    page_id = args.get("page_id") or args.get("pago_id") or ""
    concepto = args.get("concepto", "Trámite GoyaPay AI")
    try:
        monto = float(args.get("monto", 50.0))
    except (ValueError, TypeError):
        monto = 50.0
        
    email = args.get("email") or "coronahernandezs931@gmail.com"
    base_checkout_url = os.environ.get("VERCEL_CHECKOUT_URL", "https://checkout-web-seven.vercel.app/checkout")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'mxn',
                    'product_data': {
                        'name': f"GoyaPay: {concepto}",
                        'description': f"Liquidación oficial de trámite UNAM / Negocio (ID: {page_id})",
                    },
                    'unit_amount': int(round(monto * 100)),
                },
                'quantity': 1,
            }],
            mode='payment',
            customer_email=email if (email and "@" in email) else None,
            success_url=f"{base_checkout_url}?session_id={{CHECKOUT_SESSION_ID}}&page_id={page_id}&monto={monto}&concepto={urllib.parse.quote(concepto)}&email={urllib.parse.quote(email)}&stripe_success=true",
            cancel_url=f"{base_checkout_url}?page_id={page_id}&monto={monto}&concepto={urllib.parse.quote(concepto)}&email={urllib.parse.quote(email)}&stripe_cancel=true",
            metadata={
                "page_id": page_id,
                "concepto": concepto,
                "monto": str(monto),
                "email": email
            }
        )
        return {
            "status": "success",
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 15. Endpoint: Verificar Sesión de Stripe Checkout y Acreditar en Notion
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def verificar_sesion_stripe(request: Request):
    import stripe
    import requests
    import resend
    
    body = await request.json()
    args = body.get("args", body)
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return {"status": "error", "message": "STRIPE_SECRET_KEY no configurada"}
    
    stripe.api_key = stripe_key
    session_id = args.get("session_id")
    page_id = args.get("page_id") or ""
    
    if not session_id:
        return {"status": "error", "message": "Falta el identificador session_id de Stripe"}
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            meta = session.metadata or {}
            target_page_id = page_id or meta.get("page_id")
            concepto = meta.get("concepto") or "Trámite GoyaPay"
            try:
                monto = float(meta.get("monto") or (session.amount_total / 100.0))
            except (ValueError, TypeError):
                monto = session.amount_total / 100.0
                
            email = (session.customer_details.email if session.customer_details and session.customer_details.email else None) or meta.get("email") or "coronahernandezs931@gmail.com"
            
            # 1. Actualizar estado en Notion CRM
            token = os.environ.get("NOTION_API_KEY")
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            if target_page_id:
                patch_payload = {
                    "properties": {
                        "Estado": {"select": {"name": "pagado"}}
                    }
                }
                requests.patch(f"https://api.notion.com/v1/pages/{target_page_id}", headers=headers, json=patch_payload)
            
            # 2. Enviar recibo por correo con Resend
            try:
                resend.api_key = os.environ.get("RESEND_API_KEY")
                correo_agradecimiento = generar_html_correo_recibo(
                    concepto=concepto,
                    monto=monto,
                    metodo_pago="Tarjeta Bancaria (Stripe Checkout Oficial)",
                    detalle=f"Stripe ID: {session_id[-14:]} • Pago Aprobado",
                    nombre_usuario="Sergio Ethan Corona Hernández"
                )
                resend.Emails.send({
                    "from": "GoyaPay AI <onboarding@resend.dev>",
                    "to": [email],
                    "subject": f"✅ Comprobante de Pago Exitoso: {concepto} (Stripe)",
                    "html": correo_agradecimiento
                })
            except Exception as e_mail:
                print("Error enviando comprobante Stripe:", e_mail)
                
            return {
                "status": "success",
                "paid": True,
                "session_id": session_id,
                "page_id": target_page_id,
                "concepto": concepto,
                "monto": monto,
                "customer_email": email
            }
        else:
            return {"status": "pending", "paid": False, "payment_status": session.payment_status}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 16. Endpoint: Programar Publicación de Video en Redes Sociales (Zernio API)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def programar_video_zernio(request: Request):
    import requests
    import os
    import datetime
    
    body = await request.json()
    args = body.get("args", body)
    
    zernio_key = (os.environ.get("ZERNIO_API_KEY") or "").strip()
    if not zernio_key:
        return {"status": "error", "message": "ZERNIO_API_KEY no configurada"}
        
    title = args.get("title", "Video GoyaPay AI")
    content = args.get("content", "Demostración de pago con Cold Wallet Tangem y GoyaPay AI #fintech #automation")
    video_url = args.get("video_url") or "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    platforms_input = args.get("platforms", ["tiktok", "youtube"])
    scheduled_for = args.get("scheduled_for")
    publish_now = args.get("publish_now", False)
    
    headers = {
        "Authorization": f"Bearer {zernio_key}",
        "Content-Type": "application/json"
    }
    
    # Obtener mapeo de cuentas Zernio
    cuentas_map = {
        "tiktok": "6a0680525e333c05296e9803",
        "youtube": "6a0fd0a1520992756d99119e"
    }
    try:
        r_acc = requests.get("https://zernio.com/api/v1/accounts", headers=headers, timeout=10)
        if r_acc.status_code == 200:
            for acc in r_acc.json().get("accounts", []):
                plt = acc.get("platform")
                acc_id = acc.get("_id") or acc.get("id")
                if plt and acc_id:
                    cuentas_map[plt] = acc_id
    except Exception as e_acc:
        print("Warning obteniendo cuentas Zernio:", e_acc)
        
    platforms_payload = []
    for p in platforms_input:
        if isinstance(p, dict):
            platforms_payload.append(p)
        elif isinstance(p, str):
            p_lower = p.lower()
            if p_lower in cuentas_map:
                platforms_payload.append({
                    "platform": p_lower,
                    "accountId": cuentas_map[p_lower]
                })
                
    if not platforms_payload:
        platforms_payload = [
            {"platform": "tiktok", "accountId": cuentas_map.get("tiktok", "6a0680525e333c05296e9803")},
            {"platform": "youtube", "accountId": cuentas_map.get("youtube", "6a0fd0a1520992756d99119e")}
        ]
        
    post_payload = {
        "title": title,
        "content": content,
        "mediaItems": [{"type": "video", "url": video_url}],
        "platforms": platforms_payload,
        "visibility": "public"
    }
    
    if publish_now or not scheduled_for or scheduled_for == "now":
        post_payload["publishNow"] = True
    else:
        try:
            if "T" in scheduled_for and not scheduled_for.endswith("Z"):
                scheduled_for = scheduled_for + ":00.000Z" if len(scheduled_for) == 16 else scheduled_for + ".000Z"
        except Exception:
            pass
        post_payload["scheduledFor"] = scheduled_for
        post_payload["timezone"] = "America/Mexico_City"
        post_payload["status"] = "scheduled"
        
    try:
        resp = requests.post("https://zernio.com/api/v1/posts", headers=headers, json=post_payload, timeout=20)
        res_data = resp.json() if resp.status_code in [200, 201] else {}
        
        if resp.status_code in [200, 201]:
            post_obj = res_data.get("post", {})
            post_id = post_obj.get("_id") or post_obj.get("id") or "ok"
            return {
                "status": "success",
                "message": res_data.get("message", "Post procesado exitosamente"),
                "post_id": post_id,
                "scheduled_for": post_obj.get("scheduledFor") or ("Inmediato" if publish_now else scheduled_for),
                "platforms": [p["platform"] for p in platforms_payload],
                "dashboard_url": "https://zernio.com/dashboard"
            }
        else:
            return {
                "status": "error",
                "status_code": resp.status_code,
                "message": resp.text
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 17. Endpoint: Crear Web Call con Retell AI (Proxy Seguro sin exponer API Key en Frontend)
@app.function(image=image, secrets=[goyapay_secret])
@modal.fastapi_endpoint(method="POST")
async def crear_web_call(request: Request):
    import requests
    
    body = await request.json()
    args = body.get("args", body)
    
    retell_key = (os.environ.get("RETELL_API_KEY") or "").strip()
    if not retell_key:
        return {"status": "error", "message": "RETELL_API_KEY no configurada en variables de entorno"}
        
    agent_id = args.get("agent_id") or os.environ.get("RETELL_AGENT_ID") or "agent_14126a001a6e0fb2438a6765ed"
    dynamic_vars = args.get("retell_llm_dynamic_variables") or {}
    
    headers = {
        "Authorization": f"Bearer {retell_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "agent_id": agent_id,
        "retell_llm_dynamic_variables": dynamic_vars
    }
    
    try:
        r = requests.post("https://api.retellai.com/v2/create-web-call", headers=headers, json=payload, timeout=12)
        res_data = r.json() if r.status_code in [200, 201] else {}
        if r.status_code in [200, 201]:
            return res_data
        else:
            return {"status": "error", "message": r.text, "code": r.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}
