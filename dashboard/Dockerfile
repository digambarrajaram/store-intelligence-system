# Stage 1 — build the React app
FROM node:18-alpine AS builder

ARG VITE_API_URL
ARG VITE_WS_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

WORKDIR /app

COPY package.json ./

# Install all project dependencies (including dev deps for build)
RUN npm install --include=dev --legacy-peer-deps

COPY . .

# Build the React app with Vite (includes Tailwind CSS generation via PostCSS)
RUN npm run build && \
    if [ -d "dist" ]; then cp -r dist /app/output; \
    elif [ -d "build" ]; then cp -r build /app/output; \
    else echo "ERROR: No build output found. Available files:"; ls -la; exit 1; fi

# Stage 2 — serve with nginx
FROM nginx:alpine

RUN apk add --no-cache curl

COPY --from=builder /app/output /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:80/health >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
