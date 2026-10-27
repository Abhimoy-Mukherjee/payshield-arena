FROM node:20-slim
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ENV HOST=0.0.0.0 PORT=5173 BROWSER=none
EXPOSE 5173
CMD ["npm", "start"]
