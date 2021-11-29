FROM registry.cn-hangzhou.aliyuncs.com/mio101/amzlinux-python3:3.8

ENV TZ='Asia/Shanghai'

COPY deploy/requirements.txt /app/
WORKDIR /app/

RUN rpm --rebuilddb && \
    yum update -y && \
    yum install -y yum-utils && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 cache purge && \
    package-cleanup -q --leaves --all | xargs -l1 yum -y remove && \
    yum -y autoremove && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

COPY model /app/model
COPY utils /app/utils
COPY config /app/config
COPY SceneScript /app/SceneScript
