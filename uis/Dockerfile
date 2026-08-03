FROM node:22-alpine

WORKDIR /workspace/uis

COPY website/package*.json ./website/
COPY backoffice/package*.json ./backoffice/

RUN npm install --prefix website --no-audit --no-fund && npm install --prefix backoffice --no-audit --no-fund

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 3000 3001

CMD ["/usr/local/bin/start.sh"]
