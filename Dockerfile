FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate --noinput
RUN python manage.py ensure_admin --password admin12345
EXPOSE 8000
CMD ["gunicorn", "erp.wsgi:application", "--config", "gunicorn_config.py"]
