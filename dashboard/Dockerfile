# Stage 1 — build the React app
FROM node:18-alpine AS builder

ARG VITE_API_URL
ARG VITE_WS_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

WORKDIR /app

COPY package.json ./

# Install all project dependencies
RUN npm install --include=dev --legacy-peer-deps

# Tailwind v4 uses @tailwindcss/postcss, NOT tailwindcss directly as postcss plugin
# Install correct packages for Tailwind v4
RUN npm install @tailwindcss/postcss tailwindcss autoprefixer postcss --save-dev --legacy-peer-deps

# Overwrite postcss.config.js to use correct v4 plugin
RUN echo '{"plugins": {"@tailwindcss/postcss": {}}}' > postcss.config.json && \
    rm -f postcss.config.js postcss.config.cjs postcss.config.mjs

COPY . .

# postcss.config.json overrides any copied postcss.config.js from COPY . .
RUN rm -f postcss.config.js postcss.config.cjs postcss.config.mjs

RUN npm run build && \
    if [ -d "dist" ]; then cp -r dist /app/output; \
    elif [ -d "build" ]; then cp -r build /app/output; \
    else echo "ERROR: No build output found" && exit 1; fi

# Stage 2 — serve with nginx
FROM nginx:alpine

RUN apk add --no-cache curl

COPY --from=builder /app/output /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]