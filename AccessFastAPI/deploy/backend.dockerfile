FROM registry.cn-hangzhou.aliyuncs.com/mio101/amzlinux-python3:3.8

ENV TZ='Asia/Shanghai'
ENV PYTHONPATH=/app
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
#ENV POETRY_HOME /opt/poetry

ARG INSTALL_DEV=false
ARG INSTALL_JUPYTER=false

WORKDIR /app/

COPY pyproject.toml poetry.lock* start.sh gunicorn_conf.py /app/

RUN yum update -y && \
    yum install -y gcc tzdata yum-utils && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    /root/.local/bin/poetry config virtualenvs.create false && \
    bash -c "if [ $INSTALL_DEV == 'true' ] ; then /root/.local/bin/poetry install --no-root ; else /root/.local/bin/poetry install --no-root --no-dev ; fi" && \
    bash -c "if [ $INSTALL_JUPYTER == 'true' ] ; then pip3 install jupyterlab ; fi" && \
    pip3 cache purge && rm -rf $POETRY_CACHE_DIR && \
    yum remove -y gcc perl make && \
    package-cleanup -q --leaves --all | xargs -l1 yum -y remove && \
    yum -y autoremove && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    chmod +x /start.sh && \
    chmod +x /start-reload.sh

COPY ../app /app

EXPOSE 80
CMD ["/start.sh"]