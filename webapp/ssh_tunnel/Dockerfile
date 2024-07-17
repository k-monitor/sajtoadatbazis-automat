FROM alpine:3.14

RUN apk add --no-cache openssh

EXPOSE 9999
EXPOSE 1080

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
