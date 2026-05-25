FROM python:3.11-slim

# Install system dependencies — Tesseract OCR + Poppler for PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpoppler-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Run Streamlit
CMD streamlit run app.py \
    --server.port 8080 \
    --server.address 0.0.0.0 \
    --server.headless true