FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY server.js .
COPY .env.example .env

# Expose port
EXPOSE 3000

# Start the service
CMD ["npm", "start"]
