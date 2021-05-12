FROM python:3.9-alpine
ARG INSTALL_DEV=false
ARG INSTALL_JUPYTER=false
ENV PYTHONPATH=/app
ENV POETRY_HOME /opt/poetry

WORKDIR /app/

# Install Poetry
COPY pyproject.toml ./poetry.lock* ./start.sh ./gunicorn_conf.py /app/

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
#RUN apk add --no-cache --virtual .build-deps gcc libc-dev make && \
    apk add --no-cache --virtual .build-deps libffi-dev build-base gcc libc-dev make && \
#    && pip install --no-cache-dir "uvicorn[standard]" gunicorn \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    # Allow installing dev dependencies to run tests
    bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi" && \
    bash -c "if [ $INSTALL_JUPYTER == 'true' ] ; then pip install jupyterlab ; fi" && \
    apk del .build-deps gcc libc-dev make && \
    pip uninstall poetry && \
    chmod +x /start.sh && \
    chmod +x /start-reload.sh

COPY ./app /app

EXPOSE 80
CMD ["/start.sh"]