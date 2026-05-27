FROM python:3.10-slim

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# Copie des fichiers de dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code et de la configuration
COPY . .

# Cloud Run impose l'utilisation d'un port dynamique via la variable d'environnement $PORT
EXPOSE 8080

# Commande de démarrage adaptée à Cloud Run
CMD streamlit run app.py --server.port=8080 --server.address=0.0.0.0