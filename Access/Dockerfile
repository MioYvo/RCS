FROM registry.cn-hangzhou.aliyuncs.com/mio101/rcs_base:v0.0.1

WORKDIR /app/Access

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--loop", "uvloop"]