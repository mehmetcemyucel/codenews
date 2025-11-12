# 🚀 Docker Build Optimizations

This document explains how the CodeNews Docker image build pipeline stays fast and lean.

## 📦 Multi-Stage Build

The Dockerfile uses a two-stage (multi-stage) layout:

### 1. Builder Stage (Dependency Installation)
```dockerfile
FROM python:3.11-slim as builder
```
- All build tools live here
- Python dependencies are installed with cache support
- `--user` keeps packages inside the local home directory

### 2. Runtime Stage (Final Image)
```dockerfile
FROM python:3.11-slim
```
- Contains only runtime requirements
- Copies the prebuilt packages from the builder stage
- Produces a smaller, safer final image

## 💾 Build Cache Optimizations

### 1. Pip Cache Mount
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-warn-script-location -r requirements.txt
```

**Benefits**
- ✅ Caches pip downloads between builds
- ✅ Avoids re-downloading identical packages
- ✅ Cuts build times dramatically
- ✅ Reduces network usage

### 2. Layer Caching Strategy

```dockerfile
# 1. Copy requirements first
COPY requirements.txt .

# 2. Install dependencies (this layer is cached)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt

# 3. Copy the application code last
COPY . .
```

**Rationale**
- Dependencies aren’t reinstalled unless `requirements.txt` changes
- Only the final `COPY` layer rebuilds when code changes
- Most builds re-use earlier layers → faster iterations

### 3. GitHub Actions Registry Cache

`.github/workflows/deploy.yml`
```yaml
cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max
```

**Benefits**
- ✅ Stores BuildKit cache in GitHub Container Registry
- ✅ Every workflow run can pull previous cache layers
- ✅ CI/CD build times drop sharply
- ✅ `mode=max` preserves all layers

### 4. Smart Disk Cleanup (GitHub Actions)

```yaml
- name: Free Disk Space (Keep Build Cache)
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /opt/ghc
    sudo rm -rf /usr/local/share/boost
    docker image prune -f --filter "dangling=true"
```

**Strategy**
- ❌ Does not nuke the whole Docker cache (`docker system prune -af`)
- ✅ Removes only unnecessary toolchains (~15 GB)
- ✅ Keeps Docker/BuildKit cache intact
- ✅ Preserves pip cache mounts and registry cache
- 🎯 Result: frees disk space without hurting build speed

## 📊 Build-Time Comparison

### Traditional Dockerfile (No Optimization)
```
First build:    ~3-4 minutes
Code change:    ~3-4 minutes (rebuilds everything)
Dep change:     ~3-4 minutes
```

### Multi-Stage + Cache (Optimized)
```
First build:    ~3-4 minutes
Code change:    ~30 seconds (only last layer)
Dep change:     ~1-2 minutes (deps pulled from cache)
```

**Savings:** ~80–90 % faster rebuilds.

## 🔍 Image Size Optimizations

### Slim Base Image
```dockerfile
FROM python:3.11-slim
```
- Full Python image: ~900 MB
- Slim variant: ~120 MB
- **Savings:** ~780 MB

### Multi-Stage Build
```
Builder stage: exists only during build
Runtime stage: ships only what’s needed
```
- Build tools never reach production
- Smaller deployable image → faster pulls & startups

### `.dockerignore`
```
tests/
*.md
.git/
__pycache__/
```
- Keeps unnecessary files out of the build context
- Uploads a smaller context to Docker
- Produces lighter images

## 🚀 Usage

### Local Build
```bash
# Build with BuildKit
DOCKER_BUILDKIT=1 docker build -t codenews .

# Or via docker-compose
docker-compose build
```

### GitHub Actions
The optimized workflow runs automatically:
```bash
git push origin main
```

## 📈 Monitoring Cache Usage

### Inspect Cache Hits/Misses
```bash
docker build --progress=plain -t codenews .
```

### Check Registry Cache Size
GitHub repo → Packages → `codenews` → view storage usage.

## 🛠️ Advanced Optimizations

### 1. Pinned Dependency File (Recommended)
```bash
pip freeze > requirements.txt
```

### 2. Wheel Cache (Optional)
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/tmp/pip-build \
    pip install --user -r requirements.txt
```

### 3. Parallel Builds
GitHub Actions uses BuildKit, so multi-platform/parallel builds are enabled by default.

## 💡 Best Practices

1. ✅ **Change `requirements.txt` sparingly**
   - Think before adding dependencies
   - Group related additions to reduce rebuild churn

2. ✅ **Ship frequent code changes**
   - Layer caching is tuned for rapid iteration

3. ✅ **Keep `.dockerignore` current**
   - Exclude new temporary or tooling directories as they appear

4. ✅ **Prune registry cache when needed**
   ```bash
   docker buildx prune -f
   ```

## 🔧 Troubleshooting

### Cache Not Working
```bash
docker build --no-cache -t codenews .
# For GitHub Actions: re-run the workflow
```

### Builds Still Slow
```bash
docker buildx version   # ensure BuildKit is enabled
docker buildx du        # inspect cache usage
```

### Disk Is Full
```bash
docker builder prune -af   # remove unused cache
docker buildx prune -af    # remove all build caches
```

## 📚 References

- [Docker BuildKit](https://docs.docker.com/build/buildkit/)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Build cache](https://docs.docker.com/build/cache/)
- [GitHub Actions cache](https://docs.docker.com/build/ci/github-actions/cache/)

---

**💡 Bottom line:** Smarter caching + multi-stage builds = faster iterations and smaller images. 🚀
