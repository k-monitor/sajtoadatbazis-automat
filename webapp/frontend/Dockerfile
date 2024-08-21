FROM alpine

RUN apk add --update nodejs yarn

WORKDIR /app

COPY . .

RUN yarn install && yarn build

EXPOSE 3000

ENV NUXT_APP_BASE_URL="/autokmdb/"

CMD ["node", ".output/server/index.mjs"]
