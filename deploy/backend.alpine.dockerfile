FROM python:3.9-alpine
ENV TZ='Asia/Shanghai'

COPY deploy/requirements.txt /app/
WORKDIR /app/

#RUN #sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
RUN apk add --no-cache --virtual .build-deps libffi-dev build-base gcc libc-dev make && \
    pip3 install -U setuptools && \
    pip3 install --no-cache-dir -r requirements.txt && \
    apk del .build-deps gcc libc-dev make && \
    pip uninstall poetry && \
    chmod +x /start.sh && \
    chmod +x /start-reload.sh

COPY ./app /app

EXPOSE 80
CMD ["/start.sh"]