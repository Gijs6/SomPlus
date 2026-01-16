FROM python:3.13-slim
LABEL org.opencontainers.image.source https://github.com/Gijs6/SomPlus
WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
CMD ["python", "scheduler.py"]
