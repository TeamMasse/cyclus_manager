FROM alpine:latest

WORKDIR /sync

RUN apk add --no-cache bash
RUN apk add --no-cache lftp

COPY script.sh /script.sh

RUN chmod +x /script.sh

CMD ["bash", "/script.sh"]