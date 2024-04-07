FROM python:3.9 

WORKDIR /app



RUN apt-get update && apt-get install -y \
    libpulse-dev \
    swig
# Copiar el archivo de dependencias y instalarlas
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para ejecutar la aplicación Streamlit
CMD streamlit run app.py 