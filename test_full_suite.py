import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("[INFO] INICIANDO BATERIA COMPLETA DE PRUEBAS - GOYAPAY AI")
print("="*60)

# 1. VERIFICACION DE NOTION
print("\n[TEST 1] Consultando base de datos Notion...")
db_id = os.environ.get('NOTION_DATABASE_ID', '')
token = os.environ.get('NOTION_API_KEY', '')

if not token or not db_id:
    print("⚠️ NOTION_API_KEY o NOTION_DATABASE_ID no encontradas en .env. Omitiendo prueba 1.")
else:
    notion_headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
r_notion = requests.post(f'https://api.notion.com/v1/databases/{db_id}/query', headers=notion_headers)
assert r_notion.status_code == 200, f"Error Notion DB: {r_notion.text}"
notion_items = r_notion.json().get('results', [])
print(f"[*] Notion DB accesible. Total de registros: {len(notion_items)}")
for item in notion_items:
    props = item.get('properties', {})
    c = props.get('Concepto', {}).get('title', [{}])[0].get('text', {}).get('content', '')
    e = props.get('Estado', {}).get('select', {}).get('name', '')
    m = props.get('Monto', {}).get('number', 0)
    print(f"   - {c} | Estado: {e} | Monto: ${m} MXN")

# 2. VERIFICACION DE MODAL BACKEND
print("\n[TEST 2] Verificando microservicios en Modal...")
health_url = "https://coronahernandezs931--goyapay-voice-backend-health.modal.run"
r_health = requests.get(health_url)
print(f"   Health check: {r_health.status_code} -> {r_health.json()}")

# Consultar pagos
cons_url = "https://coronahernandezs931--goyapay-voice-backend-consultar-pag-33cf83.modal.run"
r_cons = requests.post(cons_url, json={"user_phone": "7772310427"})
assert r_cons.status_code == 200, f"Error consultar pagos: {r_cons.text}"
cons_data = r_cons.json()
print(f"   Consultar pagos: 200 OK -> Encontrados: {cons_data.get('has_payments')}")
if cons_data.get('primer_pago'):
    print(f"   Pago pendiente detectado: {cons_data['primer_pago']['concepto']} (${cons_data['primer_pago']['monto']} MXN)")

# 3. VERIFICACION DE ENVIO DE CORREO (RESEND)
print("\n[TEST 3] Probando envio de correo de cobro con Tangem...")
email_url = "https://coronahernandezs931--goyapay-voice-backend-enviar-correo-pago.modal.run"
target_pago_id = cons_data.get('primer_pago', {}).get('pago_id', 'demo-test')
r_email = requests.post(email_url, json={
    "correo": "coronahernandezs931@gmail.com",
    "pago_id": target_pago_id,
    "concepto": "Credencial de Biblioteca (Prueba del Sistema)",
    "monto": 120.0
})
assert r_email.status_code == 200, f"Error enviar correo: {r_email.text}"
email_data = r_email.json()
print(f"   Correo enviado exitosamente -> ID Resend: {email_data.get('email_id')}")
print(f"   URL Checkout generada: {email_data.get('checkout_url')}")

# 4. VERIFICACION DE VERCEL CHECKOUT & SIMULADOR
print("\n[TEST 4] Verificando endpoints en Vercel...")
r_vercel_home = requests.get("https://checkout-web-seven.vercel.app")
assert r_vercel_home.status_code == 200, "Error en Vercel Home"
print(f"   Simulador Web Call: {r_vercel_home.status_code} OK (HTML cargado)")

r_vercel_checkout = requests.get("https://checkout-web-seven.vercel.app/checkout")
assert r_vercel_checkout.status_code == 200, "Error en Vercel Checkout"
print(f"   Pasarela TangemPay Checkout: {r_vercel_checkout.status_code} OK (HTML cargado)")

# 5. VERIFICACION DE RETELL AI & TELEFONIA
print("\n[TEST 5] Verificando configuracion telefonica en Retell AI...")
retell_key = os.environ.get('RETELL_API_KEY', '')
test_phone = os.environ.get('TWILIO_PHONE_NUMBER', '+12318670128')

if not retell_key:
    print("⚠️ RETELL_API_KEY no encontrada en .env. Omitiendo prueba de telefonía.")
else:
    retell_headers = {'Authorization': f'Bearer {retell_key}'}
    encoded_phone = requests.utils.quote(test_phone)
    r_phone = requests.get(f'https://api.retellai.com/get-phone-number/{encoded_phone}', headers=retell_headers)
    if r_phone.status_code == 200:
        phone_data = r_phone.json()
        inbound_agents = phone_data.get('inbound_agents', [{}])
        inbound_agent = inbound_agents[0].get('agent_id') if inbound_agents else phone_data.get('inbound_agent_id')
        print(f"   Numero: {phone_data.get('phone_number')}")
        print(f"   Inbound Agent conectado: {inbound_agent}")

# Verificar agente de GoyaPay
r_agent = requests.get(f'https://api.retellai.com/get-agent/{inbound_agent}', headers=retell_headers)
assert r_agent.status_code == 200, f"Error Retell Agent: {r_agent.text}"
agent_info = r_agent.json()
print(f"   Nombre del Agente: {agent_info.get('agent_name')}")
print(f"   Voz: {agent_info.get('voice_id')}")
print(f"   Idioma: {agent_info.get('language')}")

# Verificar LLM y herramientas
llm_id = agent_info.get('response_engine', {}).get('llm_id')
r_llm = requests.get(f'https://api.retellai.com/get-retell-llm/{llm_id}', headers=retell_headers)
assert r_llm.status_code == 200, f"Error Retell LLM: {r_llm.text}"
llm_info = r_llm.json()
tools = [t.get('name') for t in llm_info.get('general_tools', [])]
print(f"   Modelo: {llm_info.get('model')}")
print(f"   Herramientas activas: {', '.join(tools)}")

print("\n" + "="*60)
print("[EXITO] TODAS LAS PRUEBAS (5/5) PASARON CON EXITO")
print("="*60)
