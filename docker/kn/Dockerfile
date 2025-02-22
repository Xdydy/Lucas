FROM python:3.10

RUN pip install flask

RUN pip install lucas[kn] --no-cache --index-url http://192.168.28.220:12121 --trusted-host 192.168.28.220

RUN mkdir -p /code && cd /code

WORKDIR /code

ENV FAASIT_PROVIDER=knative 

CMD ["bash"]