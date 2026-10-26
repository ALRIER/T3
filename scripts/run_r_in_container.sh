#!/usr/bin/env bash
# Shared pinned R execution for GitHub Actions and local Docker runners.
set -euo pipefail
IMAGE="${T2_R_IMAGE:-ghcr.io/alrier/t3-r@sha256:658e61478909fe688bc2d47837f7e09d64b4724ba1ff84bc807e901bf7931e16}"
if ! command -v docker >/dev/null 2>&1; then echo "Docker is required for T2 pinned R runtime" >&2; exit 127; fi
ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
if [[ ! -d "$ROOT" ]]; then echo "Missing workspace: $ROOT" >&2; exit 2; fi
# Match the host UID/GID so R-created checkpoints remain writable by later
# host-side Python steps (Optuna, manifests, and packaging). The previous root
# container user left artifacts/ owned by root and made the next HPO step fail.
args=(run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$ROOT:/workspace" -w /workspace)
# Forward declared experiment settings and nonsensitive Actions context.
while IFS='=' read -r key _; do
  case "$key" in
    *TOKEN*|*PASSWORD*|*SECRET*|*SSH_KEY*|*PRIVATE_KEY*) continue ;;
    T2_*|T3_*|RW2_*|HG_*|EXTERNAL_*|SHARD|MODE|FAMILY|ENGINE|SEED|R_LIBS_USER|CI|GITHUB_SHA|GITHUB_RUN_ID|OMP_NUM_THREADS|OPENBLAS_NUM_THREADS|MKL_NUM_THREADS)
      args+=(-e "$key") ;;
  esac
done < <(env)
exec docker "${args[@]}" "$IMAGE" "$@"
