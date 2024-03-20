FROM alpine:3.14
RUN apk add --no-cache openssh

EXPOSE 9999

CMD ["ssh", "-N", "-L", "9999:127.0.0.1:3306", "-p", "2267", "-i", "/secrets/autokmdb_key", "autokmdb@ahalo.hu"]