FROM node:17.6.0

WORKDIR /app

COPY ./api/package.json /app/
RUN npm install

COPY ./api /app

EXPOSE 4000
CMD ["node", "/app/api.js"]