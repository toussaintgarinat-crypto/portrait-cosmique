FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Moteur (synchronisé depuis Workplace, cf. scripts/export-portrait-cosmique.sh) — aplati
# à la racine de /app pour que `main.py` l'importe comme des modules normaux (pas de
# sys.path à gérer en prod ; le repo garde engine/ en sous-dossier pour la clarté du dépôt).
COPY engine/traditions.py engine/synthese.py engine/significations.py ./

COPY main.py llm.py ./
COPY static/ ./static/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8410
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8410/sante')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8410"]
