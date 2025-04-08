FROM python:3.12.0-bookworm



RUN apt-get update && apt-get upgrade -y && apt install xvfb -y
# install chromium
RUN apt-get install -y chromium wget unzip

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /app/screenshot/


EXPOSE 8000

CMD ["python", "main.py"]