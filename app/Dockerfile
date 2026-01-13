# Image Python officielle
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Paquets système utiles pour geopandas / fiona / pyproj
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les dépendances
COPY requirements.txt /app/requirements.txt

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . /app

# Exposer le port de Shiny
EXPOSE 8000

# Lancer l'app Shiny (app.py doit définir "app = App(...)")
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8000", "app.py"]
