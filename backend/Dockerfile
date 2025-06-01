# 1. Base image
FROM node:18-alpine

# 2. Set working directory
WORKDIR /app

# 3. Copy backend files
COPY . .

# 4. Install backend dependencies
RUN npm install

# 5. Build frontend
WORKDIR /app/frontend
RUN npm install && npm run build

# 6. Move frontend build to backend's public folder
RUN mkdir -p /app/public && cp -r dist/* /app/public/

# 7. Switch back to backend root
WORKDIR /app

# 8. Expose port and run server
EXPOSE 8080
CMD ["node", "server.js"]
