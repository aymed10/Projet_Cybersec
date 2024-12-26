import socket
import requests
from bs4 import BeautifulSoup
import re
import csv
from urllib.parse import urlparse
from datetime import datetime
from pymongo import MongoClient

# Initialize MongoDB client
mongo_client = MongoClient("mongodb://192.168.118.75:27017/")
db = mongo_client["monitoring_db"]
connections_collection = db["connections"]

def log_to_mongo(log_entry):
    print(f"[DEBUG] Log Entry: {log_entry}")
    """Log connection details to MongoDB."""
    try:
        connections_collection.insert_one(log_entry)
        print("[INFO] Log entry saved to MongoDB.")
    except Exception as e:
        print(f"[ERROR] Failed to save log: {e}")

# Load keywords and blocked URLs from CSV files
def load_keywords_from_csv(filename):
    """ Load keywords and blocked URLs from CSV files """
    keywords = []
    try:
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                keywords.extend(row)
    except Exception as e:
        print(f"[ERREUR] Chargement des mots-clés : {e}")
    return keywords

# Charger les URLs bloquées depuis un fichier CSV
def load_blocked_urls_from_csv(filename):
    """ Charger les URLs bloquées depuis un fichier CSV """
    blocked_urls = []
    try:
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                blocked_urls.append(row[0].strip())
    except Exception as e:
        print(f"[ERREUR] Chargement des URLs : {e}")
    return blocked_urls

# Extraire l'URL de la requête HTTP
def extract_url_from_request(request_data):
    """ Extraire l'URL à partir des données de requête HTTP """
    match = re.search(r"GET (.*?) HTTP", request_data)
    if match:
        url = match.group(1).strip()
        if url.startswith("/"):
            host_match = re.search(r"Host: ([^\r\n]+)", request_data)
            if host_match:
                domain = host_match.group(1).strip()
                url = f"http://{domain}{url}"
        return url
    return None

# Vérifier la présence de mots-clés sur la page
def check_for_keywords(url, keywords):
    """ Vérifie si des mots-clés apparaissent sur la page web """
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        for keyword in keywords:
            if keyword.lower() in soup.get_text().lower():
                print(f"[BLOQUÉ] Mot-clé détecté : '{keyword}' sur {url}")
                return True  # Site bloqué
        return False  # Site autorisé
    except Exception as e:
        print(f"[ERREUR] Impossible d'accéder à {url} : {e}")
        return True  # Bloquer en cas d'erreur d'accès

# Gérer les connexions et appliquer les filtres
def handle_connection(conn, keywords, blocked_urls, allowed_ips):
    """ Filtre les requêtes HTTP en fonction des règles définies """
    try:
        client_ip, client_port = conn.getpeername()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] Connexion de {client_ip}:{client_port}")

        data = conn.recv(1024).decode(errors='ignore')
        if not data:
            print(f"[AVERTISSEMENT] Aucune donnée reçue de {client_ip}")
            return

        url = extract_url_from_request(data)
        if not url:
            print(f"[AVERTISSEMENT] URL non détectée pour {client_ip}")
            conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return

        print(f"[INFO] Requête URL : {url}")

        # Create the base log entry
        log_entry = {
            "timestamp": timestamp,
            "source_ip": client_ip,
            "destination": url,
            "status": "",
            "reason": "",
            "action": ""
        }

        # Check if the IP is allowed (accès sans restriction)
        if client_ip in allowed_ips:
            print(f"[AUTORISÉ] IP autorisée : {client_ip}")
            response = requests.get(url)
            conn.sendall(b"HTTP/1.1 200 OK\r\n\r\n" + response.content)
            log_entry["status"] = "allowed"
            log_entry["action"] = "Content transmitted"
            log_to_mongo(log_entry)
            return

        # Check blocked URLs
        if any(blocked_url in url for blocked_url in blocked_urls):
            print(f"[BLOQUÉ] URL interdite : {url}")
            conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            log_entry["status"] = "blocked"
            log_entry["reason"] = "Blocked URL"
            log_entry["action"] = "Connection blocked"
            log_to_mongo(log_entry)
            return

        # Check keywords
        if check_for_keywords(url, keywords):
            print(f"[BLOQUÉ] Contenu bloqué : {url}")
            conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            log_entry["status"] = "blocked"
            log_entry["reason"] = "Keyword detected"
            log_entry["action"] = "Connection blocked"
            log_to_mongo(log_entry)
            return

        # Si tout est autorisé, transmettre le contenu de la page
        print(f"[AUTORISÉ] Accès autorisé à : {url}")
        response = requests.get(url)
        conn.sendall(b"HTTP/1.1 200 OK\r\n\r\n" + response.content)
        log_entry["status"] = "allowed"
        log_entry["action"] = "Content transmitted"
        log_to_mongo(log_entry)

    except Exception as e:
        print(f"[ERREUR] Problème lors du traitement : {e}")
    finally:
        conn.close()

# Démarrer le serveur pour intercepter les connexions HTTP
def start_server(keywords, blocked_urls, allowed_ips):
    """ Démarre le serveur de filtrage HTTP """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 9999))
    server.listen(5)
    print("[INFO] Serveur de filtrage en écoute sur le port 9999...")

    while True:
        conn, addr = server.accept()
        handle_connection(conn, keywords, blocked_urls, allowed_ips)

# Fonction principale
if __name__ == "__main__":
    # Charger les fichiers
    keywords = load_keywords_from_csv("banned_words.csv")
    blocked_urls = load_blocked_urls_from_csv("banned_sites.csv")
    allowed_ips = ["192.168.0.3","192.168.0.4"]

    if keywords and blocked_urls:
        print("[INFO] Mots-clés et URLs chargés avec succès.")
        start_server(keywords, blocked_urls, allowed_ips)
    else:
        print("[ERREUR] Aucun mot-clé ou URL bloquée trouvée. Vérifiez vos fichiers CSV.")

