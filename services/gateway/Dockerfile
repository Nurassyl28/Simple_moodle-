FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Общий пакет ставится первым: он меняется реже кода сервиса, слой кэшируется.
COPY shared /srv/shared
RUN pip install --no-cache-dir /srv/shared

COPY services/gateway/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

COPY services/gateway/gateway_app /srv/gateway_app

# Единственный сервис, публикуемый наружу.
EXPOSE 8000
CMD ["uvicorn", "gateway_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
