FROM mio101/rcs:base-v0.0.1

COPY . /app/Access/
WORKDIR /app/Access

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--loop", "uvloop"]