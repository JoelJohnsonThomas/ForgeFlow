#!/usr/bin/env bash
# build_offline_bundle.sh — produce a single .tar.gz that contains everything
# needed to deploy ForgeFlow inside an air-gapped network.
#
# Bundle contents:
#   images/         — saved docker images (api, mcp, dashboard, postgres, ollama)
#   ollama-models/  — pre-pulled Ollama models so the daemon doesn't need
#                     to phone home for weights
#   helm/forgeflow/ — copy of the Helm chart
#   k8s/            — copy of the plain-YAML manifests
#   wheels/         — pinned pip wheels for forgeflow + dev extras
#   load-and-push.sh— pushes the images into the on-prem registry
#   manifest.txt    — SHA256 sums and versions
#
# Usage:
#   ./scripts/build_offline_bundle.sh [--output FILE] [--version TAG]
#                                     [--ollama-models "model1,model2"]
#
# Requires: docker, helm, python3, tar. Internet access on the build host.

set -euo pipefail

# ---- defaults --------------------------------------------------------------
OUTPUT="forgeflow-offline.tar.gz"
VERSION="${VERSION:-0.1.0}"
OLLAMA_MODELS=""
INCLUDE_OLLAMA_IMAGE="${INCLUDE_OLLAMA_IMAGE:-true}"

# ---- arg parsing -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)         OUTPUT="$2"; shift 2 ;;
    --version)        VERSION="$2"; shift 2 ;;
    --ollama-models)  OLLAMA_MODELS="$2"; shift 2 ;;
    --no-ollama)      INCLUDE_OLLAMA_IMAGE="false"; shift ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ---- preconditions ---------------------------------------------------------
for cmd in docker tar python3 helm; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing required tool: $cmd"; exit 1; }
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STAGING="$(mktemp -d -t forgeflow-bundle.XXXXXX)"
trap 'rm -rf "$STAGING"' EXIT

BUNDLE_DIR="$STAGING/forgeflow-offline-$VERSION"
mkdir -p "$BUNDLE_DIR"/{images,ollama-models,wheels}

echo ">> Staging in $BUNDLE_DIR"

# ---- 1. Build + save container images --------------------------------------
echo ">> Building images at version $VERSION"
docker build --target api       -t "forgeflow/api:$VERSION"       "$REPO_ROOT"
docker build --target mcp       -t "forgeflow/mcp:$VERSION"       "$REPO_ROOT"
docker build --target dashboard -t "forgeflow/dashboard:$VERSION" "$REPO_ROOT"

echo ">> Pulling postgres base image"
docker pull pgvector/pgvector:pg16

IMAGES=(
  "forgeflow/api:$VERSION"
  "forgeflow/mcp:$VERSION"
  "forgeflow/dashboard:$VERSION"
  "pgvector/pgvector:pg16"
)

if [[ "$INCLUDE_OLLAMA_IMAGE" == "true" ]]; then
  echo ">> Pulling Ollama base image"
  docker pull ollama/ollama:latest
  IMAGES+=("ollama/ollama:latest")
fi

echo ">> Saving images to $BUNDLE_DIR/images/"
for img in "${IMAGES[@]}"; do
  fname="$(echo "$img" | tr '/:' '__').tar"
  docker save "$img" -o "$BUNDLE_DIR/images/$fname"
  echo "   - $fname"
done

# ---- 2. Pre-pull Ollama model weights --------------------------------------
if [[ -n "$OLLAMA_MODELS" ]]; then
  echo ">> Pre-pulling Ollama models: $OLLAMA_MODELS"
  # Start a temporary Ollama container and pull each model. The on-disk
  # blobs live in a volume we tar up afterwards.
  CID="$(docker run -d -v forgeflow-ollama-models:/root/.ollama \
                --name fb-ollama-build ollama/ollama:latest)"
  trap 'docker rm -f fb-ollama-build >/dev/null 2>&1 || true; rm -rf "$STAGING"' EXIT

  # Wait for daemon
  for _ in $(seq 1 30); do
    if docker exec fb-ollama-build ollama list >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  IFS=',' read -r -a MODELS <<< "$OLLAMA_MODELS"
  for m in "${MODELS[@]}"; do
    echo "   - pulling $m"
    docker exec fb-ollama-build ollama pull "$m"
  done

  # Snapshot the model store
  docker run --rm -v forgeflow-ollama-models:/data \
    -v "$BUNDLE_DIR/ollama-models:/out" alpine:3 \
    tar -czf /out/models.tar.gz -C /data .

  docker rm -f fb-ollama-build >/dev/null
  docker volume rm forgeflow-ollama-models >/dev/null
fi

# ---- 3. Copy Helm chart + k8s manifests ------------------------------------
echo ">> Copying Helm chart and k8s manifests"
cp -r "$REPO_ROOT/helm"         "$BUNDLE_DIR/helm"
cp -r "$REPO_ROOT/k8s"          "$BUNDLE_DIR/k8s"

# ---- 4. Download pip wheels for the dev install ----------------------------
echo ">> Downloading pip wheels"
python3 -m pip download \
  -r "$REPO_ROOT/requirements.txt" \
  --dest "$BUNDLE_DIR/wheels" \
  --no-deps 2>/dev/null || {
  echo "   (warning) some wheels could not be downloaded — review wheels/ before shipping"
}

# Also bundle requirements files for the offline pip install
cp "$REPO_ROOT/requirements.txt" "$BUNDLE_DIR/wheels/requirements.txt"
[[ -f "$REPO_ROOT/requirements-dev.txt" ]] && \
  cp "$REPO_ROOT/requirements-dev.txt" "$BUNDLE_DIR/wheels/requirements-dev.txt"

# ---- 5. Generate the on-prem loader script ---------------------------------
cat > "$BUNDLE_DIR/load-and-push.sh" <<'LOADER'
#!/usr/bin/env bash
# load-and-push.sh — load saved images and push them to an on-prem registry.
# Usage:
#   ./load-and-push.sh REGISTRY [TAG]
#   e.g. ./load-and-push.sh registry.internal.corp/forgeflow 0.1.0

set -euo pipefail

REGISTRY="${1:-}"
TAG="${2:-0.1.0}"

if [[ -z "$REGISTRY" ]]; then
  echo "Usage: $0 REGISTRY [TAG]"
  exit 1
fi

cd "$(dirname "$0")/images"

for tar in *.tar; do
  echo ">> Loading $tar"
  docker load -i "$tar"
done

# Re-tag and push the forgeflow images. Third-party images keep their
# original coordinates — push them too so on-prem nodes don't try to pull
# from the public Docker Hub.
for src in "forgeflow/api:$TAG" "forgeflow/mcp:$TAG" "forgeflow/dashboard:$TAG"; do
  component="${src#forgeflow/}"
  dest="$REGISTRY/${component}"
  echo ">> Tagging $src -> $dest"
  docker tag "$src" "$dest"
  docker push "$dest"
done

# Third-party images: push under their original names so Helm values
# pointing at the standard image refs continue to work.
for img in "pgvector/pgvector:pg16" "ollama/ollama:latest"; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    dest="$REGISTRY/${img}"
    echo ">> Pushing $img -> $dest"
    docker tag "$img" "$dest"
    docker push "$dest"
  fi
done

echo ">> Done. Helm install with image.registry=$REGISTRY"
LOADER
chmod +x "$BUNDLE_DIR/load-and-push.sh"

# ---- 6. Manifest with SHA256 sums ------------------------------------------
echo ">> Generating manifest.txt"
{
  echo "ForgeFlow Air-Gapped Bundle"
  echo "Version: $VERSION"
  echo "Built:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "SHA256 of bundled images:"
  for f in "$BUNDLE_DIR/images"/*.tar; do
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum "$f" | sed "s|$BUNDLE_DIR/||"
    else
      shasum -a 256 "$f" | sed "s|$BUNDLE_DIR/||"
    fi
  done
} > "$BUNDLE_DIR/manifest.txt"

# ---- 7. Tar the whole staging directory -----------------------------------
echo ">> Compressing to $OUTPUT"
tar -czf "$OUTPUT" -C "$STAGING" "forgeflow-offline-$VERSION"

# Final sanity check
if [[ -f "$OUTPUT" ]]; then
  SIZE="$(du -h "$OUTPUT" | cut -f1)"
  echo ">> Bundle ready: $OUTPUT ($SIZE)"
else
  echo "FAILED to produce $OUTPUT" >&2
  exit 1
fi
