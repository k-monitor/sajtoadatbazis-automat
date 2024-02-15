FROM alpine as build

RUN apk add --update nodejs npm

WORKDIR /app

COPY . .

RUN npm install && npm run build


FROM nginx as runtime

COPY --from=build /app /usr/share/nginx/html
