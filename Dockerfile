FROM python:3.12-slim as builder

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY app/app.py .

ENV PATH=/home/appuser/.local/bin:$PATH
ENV APP_VERSION=v1

USER appuser

EXPOSE 5000

CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","2","app:app" ]
