FROM 289631370416.dkr.ecr.us-east-2.amazonaws.com/rcs/rcs_pyservice/basics:3
#FROM registry.cn-hangzhou.aliyuncs.com/mio101/rcs:dev-base-v0.0.2

COPY . /app/DataProcessor/
WORKDIR /app/DataProcessor

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--loop", "uvloop", "--no-access-log"]
# must use exec first, otherwise gunicorn's masterPID will not restart correctly.
# CMD exec gunicorn -k "uvicorn.workers.UvicornWorker" --bind "0.0.0.0:8091" --graceful-timeout "5" Access.main:app