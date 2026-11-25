FROM alpine:3.14

RUN apk add --no-cache openssh

EXPOSE 9999
EXPOSE 1080

COPY known_hosts /etc/ssh/ssh_known_hosts
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
