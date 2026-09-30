FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Par défaut : l'API. L'interface utilise la même image avec une autre commande.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
