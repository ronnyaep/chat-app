FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir fastapi==0.68.1 \
    uvicorn==0.15.0 \
    jinja2==3.0.1 \
    python-multipart==0.0.5 \
    itsdangerous==2.0.1 \
    aiofiles==0.7.0 \
    starlette==0.14.2

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
