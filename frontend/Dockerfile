FROM node:alpine

WORKDIR /app

RUN npm install -g serve

COPY . .

RUN npm install

RUN npm run build

CMD ["serve", "-s", "/app/build"]
