# Independent T3 experiment archive audit

**Result:** PASS for the **recorded artifact inventory** only. Audit Actions run: https://github.com/ALRIER/T3/actions/runs/44220954147 (successful).

- GitHub Actions artifact sources: **7,983/7,983** current and archived; zero newly discovered or missing IDs.
- Zenodo files: **11/11**, comprising ten T3 series packages and file_manifest.csv.
- Stored original bytes: **45,354,058,307**, distributed over **7,994 manifest records** and **8,187 Git LFS chunk pointers**.
- All recorded manifests and pointers passed structural, size, and SHA-256-ID consistency checks.
- **Seven** representative archives (one per repository archive category) were fetched via Git LFS, reconstructed, and checked against original SHA-256 and ZIP member integrity.
- Major run artifact counts cross-checked: MC run 40239277660 (540), Discovery 41113724413 (231) and 41487091262 (3), Held Out 42045005791 (20) and 42050564002 (1), original Stress 42062234485 (20), fresh/adapted Stress 42092352487 (550), Real World 42390283887 (1249) and 43098925126 (21).

## Scope and still-unverified areas

1. This was **not** a 45.35 GB physical download and SHA-256 recalculation of every underlying Git LFS object. Seven independently reconstructed examples passed; all pointers were checked.
2. GitHub Actions job logs, caches, and runner-local temporary/intermediate files that were never uploaded as artifacts are **not included** in the artifact backup. Some may provide useful provenance; already-expired or never-persisted files may be impossible to recover.
3. A source-inventory pass does **not** prove that every expected experimental cell, seed, checkpoint, replication, or paired comparison is scientifically complete or valid. Those require a separate stage-level results coverage and lineage audit, ideally before publication.
4. All Git LFS source bytes must remain available on GitHub; the repository stores Git LFS **pointers**, not the binary bytes directly in Git history.

**Next recommended controls:** full sharded Git LFS download/reconstruction/SHA-256 audit, per-stage scientific contracts and checkpoint-to-source crosswalk, and retention of relevant workflow logs and this audit report independently from expiring Actions artifacts.
