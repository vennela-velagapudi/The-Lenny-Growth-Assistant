FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code (this might be overridden by docker-compose volumes during dev)
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Start the Vite development server bound to all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
