FROM python:3.10-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie des dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du projet
COPY . .

# Port fixe requis par la console Cloud Run
EXPOSE 8080

# Exécution sécurisée via le module Python pour éviter le "not found"
CMD python -m streamlit run app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false