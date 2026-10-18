# Dev client image: node 22 + npm ci into the image layer; compose bind-mounts
# live source over /app and shadows node_modules with an anonymous volume
# seeded from this layer (the express/spring family pattern). Build context:
# repo root. client/package.json arrives in Phase 0.C — until then this image
# cannot build; that is the recorded plan, not a defect.
FROM node:22-bookworm

WORKDIR /app

# Lockfile-first install keeps the dependency layer cacheable.
COPY client/package.json client/package-lock.json ./
RUN npm ci

COPY client/ ./

EXPOSE 5174
# --host keeps Vite bound to 0.0.0.0 so the published port works from the
# host browser; the port itself (5174) is set by vite.config.ts.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
