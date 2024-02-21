FROM alpine

RUN apk add --update nodejs yarn

WORKDIR /app

COPY . .

RUN yarn install && yarn build

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
