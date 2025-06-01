# Stage 1: Build frontend
FROM node:18-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Setup backend and serve frontend
FROM node:18-alpine
WORKDIR /app

# Copy backend code
COPY package*.json ./
RUN npm install
COPY . .

# Copy frontend build to public folder
RUN mkdir -p public && cp -r frontend/dist/* public/

EXPOSE 8080
CMD ["node", "server.js"]
