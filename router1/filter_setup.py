#!/usr/bin/env python3

import os
import subprocess
import shutil

# Fonction pour exécuter des commandes shell
def run_command(command):
    print(f"[INFO] Exécution : {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERREUR] {result.stderr}")
    else:
        print(result.stdout)

# Installer Squid et Apache pour la redirection
def install_packages():
    print("[INFO] Installation des paquets nécessaires...")
    run_command("apt-get update")
    run_command("apt-get install -y squid apache2")

# Configurer le proxy Squid
def configure_squid(banned_sites_csv, banned_words_csv):
    print("[INFO] Configuration de Squid...")
    banned_sites = "/etc/squid/banned_sites.txt"
    banned_words = "/etc/squid/banned_words.txt"
    squid_conf = "/etc/squid/squid.conf"

    # Convertir les fichiers CSV en fichiers plats
    shutil.copy(banned_sites_csv, banned_sites)
    shutil.copy(banned_words_csv, banned_words)

    # Configuration de Squid
    squid_config_content = f"""
    # Bloquer les sites spécifiques (HTTP et HTTPS via SNI)
    acl banned_sites dstdomain "{banned_sites}"
    http_access deny banned_sites

    # Bloquer les mots-clés spécifiques
    acl banned_keywords url_regex "{banned_words}"
    http_access deny banned_keywords

    # Redirection vers une page HTML en cas de blocage
    deny_info http://192.168.0.1/blocked.html banned_sites
    deny_info http://192.168.0.1/blocked.html banned_keywords

    # Autoriser le reste
    http_access allow all
    """

    # Écrire dans squid.conf
    with open(squid_conf, "w") as f:
        f.write(squid_config_content)

    run_command("service squid restart")
    print("[INFO] Squid configuré avec succès.")

# Configurer Apache pour la page de redirection
def configure_apache():
    print("[INFO] Configuration du serveur Apache...")

    # Chemin de la page HTML de redirection
    html_path = "/var/www/html/blocked.html"

    # Contenu HTML pour la page bloquée
    blocked_page_content = """
    <html>
    <head>
        <title>Accès Bloqué</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f8d7da;
                color: #721c24;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                text-align: center;
            }
            h1 {
                font-size: 2.5em;
            }
            p {
                font-size: 1.2em;
            }
        </style>
    </head>
    <body>
        <div>
            <h1>Accès à cette page bloqué</h1>
            <p>Ce site est interdit par l'administrateur réseau.</p>
            <p>Pour plus d'informations, contactez le support IT.</p>
        </div>
    </body>
    </html>
    """

    # Créer le fichier blocked.html
    try:
        with open(html_path, "w") as f:
            f.write(blocked_page_content)
        print(f"[INFO] Page HTML créée : {html_path}")
    except Exception as e:
        print(f"[ERREUR] Impossible de créer la page HTML : {e}")
        return

    # Redémarrer le service Apache pour s'assurer que la page est servie
    run_command("service apache2 restart")
    print("[INFO] Serveur Apache configuré avec succès.")

def main():
    print("[INFO] Début de la configuration du filtre...")
    # Déterminer le dossier où se trouve ce script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    banned_sites_csv = os.path.join(script_dir, "banned_sites.csv")
    banned_words_csv = os.path.join(script_dir, "banned_words.csv")

    # Vérifier que les fichiers CSV existent
    if not os.path.exists(banned_sites_csv) or not os.path.exists(banned_words_csv):
        print("[ERREUR] Les fichiers CSV des sites et mots interdits sont introuvables.")
        return

    # Installer les paquets nécessaires
    install_packages()

    # Configurer Squid
    configure_squid(banned_sites_csv, banned_words_csv)

    # Configurer Apache pour la redirection
    configure_apache()

    print("[INFO] Configuration complète. Squid et Apache sont prêts !")

if __name__ == "__main__":
    main()

