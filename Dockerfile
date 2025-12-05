# use an officila python runtime as a parent image
FROM python:3.11-slim

# set environment variables
ENV PYTHONWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# set work directory
WORKDIR /app

# install system dependencies (the heavy part)
# weasyprint needs these c-libraries (pango, cairo, gdk) to render pdfs
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0.0 \
    libharfbuzz-subset0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libmemcached-dev \
    && rm -rf /var/lib/apt/lists/*

# install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the project
COPY . /app/

# start the server (gunicorn)
# we use port 8000 inside the container
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "library_management.wsgi:application"]