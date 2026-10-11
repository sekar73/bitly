FROM nginx:1.28-alpine
COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY app/static /usr/share/nginx/html/static
COPY app/static/index.html /usr/share/nginx/html/index.html
