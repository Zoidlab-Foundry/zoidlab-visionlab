FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
ENV PORT=3704
EXPOSE 3704
CMD ["npm", "run", "start"]
