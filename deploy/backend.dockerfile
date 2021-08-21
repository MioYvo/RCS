FROM registry.cn-hangzhou.aliyuncs.com/mio101/amzlinux-python3:3.8

ENV TZ='Asia/Shanghai'
#ENV PYTHONPATH=/app
#ENV POETRY_CACHE_DIR=/tmp/poetry_cache


COPY deploy/requirements.txt /app/
WORKDIR /app/

RUN yum update -y && \
    yum install -y yum-utils && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
#    poetry config virtualenvs.create false && \
#    poetry install --no-root --no-dev && \
#    pip3 cache purge && \
#    rm -rf $POETRY_CACHE_DIR && \
#    poetry export -f requirements.txt --output requirements.txt && \
    pip3 install --no-cache-dir -r requirements.txt && \
#    pip3 cache purge && \
#    yum remove -y gcc perl make && \
    package-cleanup -q --leaves --all | xargs -l1 yum -y remove && \
    yum -y autoremove && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

#COPY model/ utils/ config/ /app/./
COPY model /app/model
COPY utils /app/utils
COPY config /app/config
COPY SceneScript /app/SceneScript


#EXPOSE 80
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port 9000", "--loop", "uvloop"]