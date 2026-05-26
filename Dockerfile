FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/screenshots

RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser
CMD ["python", "bot.py"]
