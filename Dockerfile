FROM nikolaik/python-nodejs

RUN apt update && apt install -y git

RUN pip install --upgrade pip

WORKDIR /app
COPY ./src ./src
COPY requirements.txt /app
RUN pip install -r requirements.txt
