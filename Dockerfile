# Base micromamba (Ubuntu 22.04) — parfait pour conda-forge
FROM mambaorg/micromamba:1.5.10-jammy

# Dossier de travail
WORKDIR /app

# Crée l’environnement en amont (cache Docker efficace)
COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n app -f /tmp/environment.yml && \
    micromamba clean --all --yes

# Toutes les commandes suivantes s’exécutent DANS l’env conda "app"
SHELL ["micromamba", "run", "-n", "app", "/bin/bash", "-lc"]

# Copie du code
COPY . /app

# Render fournit la variable PORT. Expose localement 8000 pour tests
ENV PORT=8000
EXPOSE 8000

# Démarrage Shiny (ASGI), l’app est "app:app" dans app.py
CMD shiny run --host 0.0.0.0 --port $PORT app:app
