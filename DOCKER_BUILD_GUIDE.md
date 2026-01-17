# QBench Docker Build & Test Guide

This guide covers building and testing the QBench green agent (evaluator) and purple agent (baseline) Docker images for AgentBeats deployment.

---

## Prerequisites

- Docker Desktop installed and running
- GitHub account with Container Registry access
- OpenAI API key (for purple agent testing)

---

## Part 1: Build Docker Images

### 1.1 Build Green Agent (Evaluator)

```bash
cd /Users/jyotiranjandas/Downloads/QBench/qbench

# Build for linux/amd64 (AgentBeats requirement)
docker build \
  --platform linux/amd64 \
  -t qbench-evaluator:latest \
  -f Dockerfile.qbench-evaluator \
  .

# Verify image
docker images | grep qbench-evaluator
```

**Expected output:**
```
qbench-evaluator    latest    abc123def456    1 minute ago    500MB
```

---

### 1.2 Build Purple Agent (Baseline)

```bash
cd /Users/jyotiranjandas/Downloads/QBench/qbench

# Build for linux/amd64
docker build \
  --platform linux/amd64 \
  -t qbench-purple-baseline:latest \
  -f Dockerfile.purple-agent-baseline \
  .

# Verify image
docker images | grep qbench-purple-baseline
```

**Expected output:**
```
qbench-purple-baseline    latest    def456ghi789    1 minute ago    600MB
```

---

## Part 2: Test Docker Images Locally

### 2.1 Test Green Agent

**Start the container:**
```bash
docker run -d \
  --name test-green-agent \
  -p 9009:8080 \
  qbench-evaluator:latest
```

**Check if it's running:**
```bash
# Wait a few seconds for startup
sleep 5

# Test health endpoint
curl http://localhost:9009/.well-known/a2a

# Check logs
docker logs test-green-agent
```

**Expected response:**
```json
{
  "name": "QBenchEvaluator",
  "description": "QBench - Queue Management Benchmark...",
  "url": "http://0.0.0.0:8080/",
  ...
}
```

**Cleanup:**
```bash
docker stop test-green-agent
docker rm test-green-agent
```

---

### 2.2 Test Purple Agent

**Start the container:**
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-proj-your-key-here"

docker run -d \
  --name test-purple-agent \
  -p 9019:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  qbench-purple-baseline:latest
```

**Check if it's running:**
```bash
# Wait for startup
sleep 5

# Test health endpoint
curl http://localhost:9019/.well-known/a2a

# Check logs
docker logs test-purple-agent
```

**Expected response:**
```json
{
  "name": "GPT52PurpleAgent",
  "description": "GPT-5.2 based purple agent...",
  ...
}
```

**Cleanup:**
```bash
docker stop test-purple-agent
docker rm test-purple-agent
```

---

### 2.3 Test Full Integration (Green + Purple)

**Create a test scenario:**
```bash
# Start both agents
export OPENAI_API_KEY="sk-proj-your-key-here"

docker run -d \
  --name green-agent \
  -p 9009:8080 \
  qbench-evaluator:latest

docker run -d \
  --name purple-agent \
  -p 9019:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  qbench-purple-baseline:latest

# Wait for startup
sleep 10

# Send test evaluation request to green agent
curl -X POST http://localhost:9009/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "participants": {
      "agent": "http://purple-agent:8080"
    },
    "config": {
      "scenario_types": ["backlog_cap_stability_guard"],
      "seeds": [1],
      "parallel": 1,
      "verbose": false
    }
  }'
```

**Note:** This may not work perfectly due to Docker networking. For full testing, use Docker Compose (see below).

**Cleanup:**
```bash
docker stop green-agent purple-agent
docker rm green-agent purple-agent
```

---

## Part 3: Push to GitHub Container Registry

### 3.1 Login to GHCR

```bash
# Create GitHub Personal Access Token:
# GitHub → Settings → Developer settings → Personal access tokens
# → Tokens (classic) → Generate new token
# Check: write:packages, read:packages

# Login
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

**Expected output:**
```
Login Succeeded
```

---

### 3.2 Tag and Push Green Agent

```bash
# Tag with your GitHub username
docker tag qbench-evaluator:latest ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:v1.0
docker tag qbench-evaluator:latest ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:latest

# Push
docker push ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:v1.0
docker push ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:latest
```

---

### 3.3 Tag and Push Purple Agent

```bash
# Tag
docker tag qbench-purple-baseline:latest ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:v1.0
docker tag qbench-purple-baseline:latest ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:latest

# Push
docker push ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:v1.0
docker push ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:latest
```

---

### 3.4 Make Packages Public (Optional)

To allow anyone to pull your images without authentication:

1. Go to `https://github.com/YOUR_USERNAME?tab=packages`
2. Click on the package name (e.g., `qbench-evaluator`)
3. Package settings → Change visibility → Public
4. Confirm

---

## Part 4: Test Pulled Images

```bash
# Pull from GHCR
docker pull ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:v1.0
docker pull ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:v1.0

# Test (same as Part 2)
docker run -d -p 9009:8080 ghcr.io/YOUR_GITHUB_USERNAME/qbench-evaluator:v1.0
docker run -d -p 9019:8080 -e OPENAI_API_KEY=$OPENAI_API_KEY ghcr.io/YOUR_GITHUB_USERNAME/qbench-purple-baseline:v1.0
```

---

## Troubleshooting

### Issue: "docker: command not found"
**Solution:** Install Docker Desktop from https://www.docker.com/products/docker-desktop/

### Issue: "permission denied while trying to connect to Docker daemon"
**Solution:** Make sure Docker Desktop is running

### Issue: "manifest for linux/amd64 not found"
**Solution:** Always build with `--platform linux/amd64`

### Issue: Container exits immediately
**Solution:** Check logs with `docker logs <container-name>`

### Issue: Purple agent fails with "OPENAI_API_KEY not set"
**Solution:** Pass API key with `-e OPENAI_API_KEY=sk-...`

---

## Next Steps

After successfully building and testing both Docker images:

1. ✅ Register green agent on AgentBeats
2. ✅ Register purple agent on AgentBeats
3. ✅ Create leaderboard repository
4. ✅ Set up GitHub Actions workflow
5. ✅ Test full submission flow

See `LEADERBOARD_SETUP.md` for next steps.
