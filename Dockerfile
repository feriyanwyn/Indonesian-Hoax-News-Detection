# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for compiling C++ extensions (e.g. Sastrawi, numpy, scikit-learn dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK resources so they are baked into the image
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

# Pre-download the transformer models to bake them in the image (helps offline container runs and speeds up startup)
RUN python -c "from transformers import AutoTokenizer, AutoModel; AutoTokenizer.from_pretrained('indobenchmark/indobert-base-p1'); AutoModel.from_pretrained('indobenchmark/indobert-base-p1')"

# Copy the rest of the application code
COPY . .

# Create the models directory to store trained models
RUN mkdir -p models

# Expose Streamlit default port
EXPOSE 8501

# Streamlit-specific configurations and launch command
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
