# Use Node.js 18 Alpine base image
FROM node:18-alpine

# Set working directory inside container
WORKDIR /app

# Copy package.json and package-lock.json first for caching dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all project files into container
COPY . .

# Expose port 8080 (your app listens here)
EXPOSE 8080

# Start the server
CMD ["node", "server.js"]
