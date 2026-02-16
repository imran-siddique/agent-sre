FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
COPY examples/ examples/

RUN pip install --no-cache-dir -e .

CMD ["python", "examples/quickstart.py"]
