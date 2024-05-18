FROM node:alpine

WORKDIR /app

RUN npm install -g serve

COPY build/ .

CMD ["serve", "-s", "/app"]


