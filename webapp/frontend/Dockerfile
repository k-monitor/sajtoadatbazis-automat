FROM alpine

RUN apk add --update nodejs yarn

WORKDIR /app

COPY . .

RUN yarn build && node .output/server/index.mjs
