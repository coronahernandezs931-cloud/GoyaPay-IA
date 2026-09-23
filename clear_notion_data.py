import os, sys, requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

NOTION_KEY = os.environ.get('NOTION_API_KEY')
NOTION_DB = os.environ.get('NOTION_DATABASE_ID')

if not NOTION_KEY or not NOTION_DB:
    print("❌ Error: Debes configurar NOTION_API_KEY y NOTION_DATABASE_ID en tu archivo .env")
    sys.exit(1)

HEADERS = {
    'Authorization': f'Bearer {NOTION_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

DBS_TO_CLEAR = [
    ('GoyaPay Pagos', NOTION_DB)
]

def clear_database(name, db_id):
    if not db_id:
        print(f"⚠️ No se encontró el ID para {name}")
        return
    
    print(f"Buscando registros en {name}...")
    r = requests.post(f'https://api.notion.com/v1/databases/{db_id}/query', headers=HEADERS, json={})
    
    if r.status_code != 200:
        print(f"❌ Error leyendo {name}: {r.text}")
        return
        
    pages = r.json().get('results', [])
    if not pages:
        print(f"✅ {name} ya está vacía.")
        return
        
    print(f"Borrando {len(pages)} registros de {name}...")
    for page in pages:
        page_id = page['id']
        requests.patch(f'https://api.notion.com/v1/pages/{page_id}', headers=HEADERS, json={'archived': True})
    
    print(f"✅ {name} limpiada exitosamente.")

if __name__ == "__main__":
    print("🧹 Iniciando limpieza de bases de datos en Notion...")
    for name, db_id in DBS_TO_CLEAR:
        clear_database(name, db_id)
    print("✨ ¡Limpieza completada! Todo limpio para tus nuevas pruebas.")
