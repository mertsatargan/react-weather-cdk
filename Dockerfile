# Build the app
FROM node:18-alpine AS builder
WORKDIR /app
COPY . .

# Accept build argument
ARG VITE_APP_ID
ENV VITE_APP_ID=$VITE_APP_ID

RUN npm install
RUN npm run build

# Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD [ "nginx", "-g", "daemon off;" ]