FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

# TradingAgents remains an untouched, pinned submodule. Installing it editable
# keeps the runtime import path identical to local development and makes an
# explicit submodule update visible without copying its code into the adapter.
COPY tradingagents-core ./tradingagents-core
RUN python -m pip install --no-cache-dir -e ./tradingagents-core

COPY backend ./backend

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
