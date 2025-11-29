FROM nginx:stable

RUN apt-get update && \
    apt-get install -y --no-install-recommends certbot && \
    rm -rf /var/lib/apt/lists/*

COPY conf.d/vpppn.conf.template /etc/nginx/conf.d/vpppn.conf.template
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && mkdir -p /var/www/certbot

ENV SERVER_NAME=example.com
ENV EMAIL=admin@example.com
ENV UPSTREAM_PORT=8000

ENTRYPOINT ["/entrypoint.sh"]
