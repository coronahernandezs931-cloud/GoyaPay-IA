import json
import urllib.request
import os

def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": ""
        }
    
    if request.method != "POST":
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Method not allowed"})
        }

    try:
        body = json.loads(request.body) if isinstance(request.body, str) else request.body
        page_id = body.get("page_id")
        
        if not page_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"status": "error", "message": "Falta page_id"})
            }
        notion_key = os.environ.get("NOTION_API_KEY", "")
        if not notion_key:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"status": "error", "message": "NOTION_API_KEY no configurada"})
            }

        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = json.dumps({
            "properties": {
                "Estado": {
                    "select": {
                        "name": "pagado"
                    }
                }
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {notion_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            method="PATCH"
        )
        
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"status": "success", "page_id": page_id, "estado": "pagado"})
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"status": "error", "message": str(e)})
        }
