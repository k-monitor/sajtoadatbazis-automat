FROM node

WORKDIR /app

COPY . .

RUN npm install && npm run build

EXPOSE 3000

ENV NUXT_APP_BASE_URL="/autokmdb/"

CMD ["node", ".output/server/index.mjs"]
