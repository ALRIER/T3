# T3 analytical runtime policy (R1–R4 and future reviewer analyses)

The canonical prebuilt **R analysis** environment is hosted in GitHub Container Registry and pinned by **digest** in `config/T3_DEFAULT_ANALYSIS_RUNTIME.env`. This registry image was already used by T3 experimental workflows.

All **new R analysis jobs** should call:

```bash
bash scripts/run_t3_default_analysis.sh Rscript scripts/my_analysis.R ARG1 ARG2
```

The launcher reads the centrally maintained digest, ensures an existing `T2_R_IMAGE` does not silently override it, and executes the shared `scripts/run_r_in_container.sh` wrapper with the correct workspace volume and host user ID. On private GHCR packages, use `docker/login-action@v3` with `secrets.GITHUB_TOKEN` and `packages: read`.

The default for future matrix jobs is `max-parallel: 20`; keep it at or below the repository's established hard constraint of 22. Python-only analyses may run on the hosted Python runner, unless a compatible prebuilt Python image has been verified and pinned separately.

**Important:** GitHub repositories cannot hold a permanently running Docker/Kubernetes environment. GitHub-hosted runners are ephemeral; they will pull the already-built image for each new job when needed. This avoids repeated R installations and reduces variability, but not every cold pull or input-backup reconstruction. Persistent image caches require self-hosted infrastructure, which has not been established for this repository.

Do not silently rewrite old workflows; preserve successful runs and their original code revisions. Centralize new workflows first, and migrate existing workflows only when an actual change is required. Saved scientific data should continue to live in original verified backups and immutable `R1/`, `R2/`, `R3/`, or `R4/` result folders, independent of the transient container.
