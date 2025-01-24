#!/bin/bash

# Vérifier si l'utilisateur est root
if [ "$EUID" -ne 0 ]; then
  echo "Veuillez exécuter ce script en tant que root."
  exit 1
fi

# Mettre à jour le système
echo "Mise à jour des dépôts..."
apt-get update -y && apt-get upgrade -y

# Installer les dépendances nécessaires
echo "Installation des outils nécessaires..."
apt-get install -y apt-transport-https curl gnupg

# Ajouter le dépôt Tor
echo "Ajout du dépôt officiel de Tor..."
curl -fsSL https://deb.torproject.org/torproject.org.asc | gpg --dearmor -o /usr/share/keyrings/tor-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/tor-archive-keyring.gpg] https://deb.torproject.org/torproject.org $(lsb_release -cs) main" > /etc/apt/sources.list.d/tor.list

# Mettre à jour les dépôts
echo "Mise à jour des dépôts avec Tor inclus..."
apt-get update -y

# Installer Tor
echo "Installation de Tor..."
apt-get install -y tor

# Instructions finales
echo "service tor start..."
