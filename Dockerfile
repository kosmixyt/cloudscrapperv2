FROM python:3.13.3-bookworm

RUN apt-get update && apt-get upgrade -y && apt install xvfb -y
# install chromium
RUN apt-get install -y chromium wget unzip

WORKDIR /app
COPY . .

# Remove the database and .env file after copying files
RUN rm -f sql_app.db .env

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /app/screenshot/
RUN pip install -U seleniumbase

EXPOSE 8000

CMD ["python", "main.py"]