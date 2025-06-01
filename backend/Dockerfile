# Stage 1: Build frontend
FROM node:18-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Backend + serve frontend
FROM node:18-alpine
WORKDIR /app

# Copy backend files and install dependencies
COPY package*.json ./
RUN npm install
COPY . .

# Copy frontend build output to /app/public
COPY --from=frontend-builder /app/frontend/dist ./public

EXPOSE 8080
CMD ["node", "server.js"]
