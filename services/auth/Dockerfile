FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Общий пакет ставится первым: он меняется реже кода сервиса, слой кэшируется.
COPY shared /srv/shared
RUN pip install --no-cache-dir /srv/shared

COPY services/auth/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

COPY services/auth/app /srv/app

# Сервис не публикуется наружу — снаружи только gateway.
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
