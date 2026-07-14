# Streamlit executive dashboard — deployable to Railway (or any container host).
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT at runtime; default to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080

# Shell form so $PORT is expanded at container start.
CMD streamlit run app.py \
    --server.port ${PORT} \
    --server.address 0.0.0.0 \
    --server.headless true
