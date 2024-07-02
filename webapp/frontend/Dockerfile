FROM alpine

RUN apk add --update nodejs yarn

WORKDIR /app

COPY . .

RUN yarn install && BASE_URL="https://autokmdb.deepdata.hu/autokmdb" yarn build

EXPOSE 3000

ENV NUXT_APP_BASE_URL="/autokmdb/"

CMD ["node", ".output/server/index.mjs"]
