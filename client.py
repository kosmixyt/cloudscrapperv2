import requests
import json

# Configuration
API_URL = "http://127.0.0.1:8000/proxy"
TOKEN = "votre_token_jwt_ici"  # Obtenu après connexion avec /login

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Données de la requête proxy
proxy_data = {
    "target_url": "https://example.com",
    "method": "GET",
    "headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
}

# Envoi de la requête au proxy
response = requests.post(API_URL, headers=headers, json=proxy_data)

# Affichage des résultats
if response.status_code == 200:
    proxy_response = response.json()
    print(f"Status Code: {proxy_response['status_code']}")
    print(f"Headers: {json.dumps(proxy_response['headers'], indent=2)}")
    print(f"Content: {proxy_response['content'][:200]}...")  # Affiche les 200 premiers caractères
else:
    print(f"Erreur: {response.status_code}")
    print(response.text)
