# T3 — canonical development repository for T2 V3 B3 / prospective B4

**Source of truth for all new work:** [ALRIER/T3](https://github.com/ALRIER/T3). Historical and already executed experiments remain immutable in [ALRIER/T2](https://github.com/ALRIER/T2).

## Migration
- Copied the latest B3 scientific source, experiment scripts, current B3 workflows, runtime Dockerfile, and core configuration from T2 branch `t2-v3-contract-adapter-20261024` (snapshot 2026-10-25).
- Source modules include Monte Carlo, four optimization motors (GA / NSGA-II / DE / Dirichlet), full estimator library, nested 5x3 splits, MAD 2.5 sensitivity, candidate evaluation and Real World inference.
- New pinned R container **image recipe** resides in `docker/Dockerfile.r-runtime`; publish to GHCR using `.github/workflows/t3-publish-r-runtime.yml` as `ghcr.io/alrier/t3-r:4.3.3-statmod-v1`.
- Prospective contamination grid **metadata** generator: `scripts/t2_v3_b3_generate_grid321.py`.

## CRITICAL production blockade
**T3 is not yet approved for full Monte Carlo / Discovery / Held-out / Stress / Real World execution.** Migrated production workflows include historical T2 `run-id` references and B3 scientific input code still asserts 121 scenarios. Generating the 321-design CSV does **not** update Monte Carlo generation, input schemas, frozen model interfaces or downstream artifacts. Never dispatch a full inherited workflow as the new experiment.

See `docs/T3_READINESS_AND_MIGRATION.md` for the precise gates and remediation. The old 121-scenario Discovery run #40153358036 must remain archival; do not mix old W or Monte Carlo shards with the forthcoming 321-scenario experimental release.

## Verification
- The prospective method gate runs the MAD cutoff, partition separation, full benchmark Pareto, stability and ablation synthetic smoke tests.
- The image build is an isolated publishing task, **not** scientific Monte Carlo.
- Before any full run, the 321-scenario end-to-end smoke, provenance checks, versioned outputs, storage capacity and scientific comparability requirements must pass.


## Índice de ampliaciones metodológicas B3 — registro de desarrollo (2026-10-25)

Este índice registra cambios propuestos o incorporados durante la revisión reciente de T3/B3. **No constituye evidencia de validación experimental.** Cada punto deberá desarrollarse después con definición matemática, motivación, pseudocódigo cuando aplique, criterios de aceptación y resultados reproducibles. Los artefactos históricos de T2 no son insumos permitidos para la nueva ejecución.

### A. Diseño experimental y generación Monte Carlo
1. **Diseño prospectivo de 321 escenarios**: contaminación, escala MAD, mecanismos y caso limpio; enumeración y balance del grid. Verificar coherencia entre generador, metadatos y consumidores.
2. **Calibración y sensibilidad al umbral MAD**: definición del umbral, análisis de puntos de corte y justificación frente a mecanismos y magnitudes de contaminación.
3. **Reutilización controlada de muestras Monte Carlo**: semillas, números aleatorios comunes cuando proceda, trazabilidad, reproducibilidad y prevención de filtraciones.
4. **Contrato universal versionado de datos**: interfaz común, integridad/procedencia, identificadores, 26 componentes y pesos W; permitir ejecución independiente de Monte Carlo, Discovery, Held-out, Stress y Real World sin depender de artefactos de T2.
5. **Separación estricta de roles experimentales**: semillas de entrenamiento, folds anidados, confirmación Held-out, Stress y Real World; particiones disjuntas y pruebas automáticas.

### B. Discovery: modelos y optimización
6. **Inventario y evaluación comparable de 26 estimadores clásicos**: definiciones, elegibilidad y comparación completa frente a cuatro motores principales y dos controles no evolutivos.
7. **Regla predefinida común de elección de W**: normalización MSE/Q95 mediante referencias calculadas solo en entrenamiento; objetivo combinado, desempates, pesos no negativos y suma unitaria.
8. **Cuatro motores principales**: GA, NSGA-II, DE y Dirichlet; diferencias de búsqueda y condiciones compartidas.
9. **Controles no evolutivos**: optimización convexa restringida de MSE mediante descenso proyectado aproximado y búsqueda local determinista. Distinguir solución aproximada de prueba de optimalidad global.
10. **Equidad del presupuesto de optimización**: mismo techo de evaluaciones por candidato y escenarios comparables; registrar evaluaciones efectivas, tiempo, recursos y presupuesto total de búsqueda de hiperparámetros.
11. **Early stopping inteligente**: generaciones mínimas, paciencia adaptativa, ventanas de mejora y ahorro de evaluaciones. Declarar cómo se aplica a los cuatro motores y a los controles por bloques; auditar reanudaciones.
12. **Curvas de convergencia MSE/Q95**: trayectoria frente a evaluaciones acumuladas, normalización común y comparaciones sobre puntos equivalentes, sin ocultar paradas anticipadas.
13. **Optimización anidada 5×3 y Optuna**: búsqueda interior, reajuste en folds exteriores, selección prospectiva de hiperparámetros y controles contra fuga de información.
14. **Ablaciones factoriales de regularización y DRO**: cuatro condiciones on/on, on/off, off/on y off/off. Precisar que el DRO actualmente propuesto combina promedio y peor banda de contaminación; evaluar su significado y sensibilidad. Distinguir prueba exploratoria acotada de ablación confirmatoria.
15. **Estabilidad de W**: comparar pesos congelados por motor y familia entre semillas, folds y tamaños muestrales mediante L1, L2, máximo absoluto y similitud coseno; agregar intervalos y variabilidad.

### C. Inferencia y transferencia fuera de muestra
16. **Calibración de falsos positivos que repite la selección completa**: cada réplica nula debe repetir búsqueda, ajuste, selección de W y confirmación con muestras independientes; valores p empíricos y ajuste maxT sujeto a supuestos del nulo.
17. **Transferencia a vecindarios y mecanismos excluidos**: excluir prospectivamente combinaciones del entrenamiento y evaluar mecanismos exclusivos, vecindarios exclusivos y exclusiones simultáneas.
18. **Held-out independiente con 32 referencias**: los 26 clásicos, los cuatro motores y dos controles convencionales; modelos congelados, semillas reservadas, sin reentrenar sobre confirmación. Aclarar que Held-out no debe utilizarse como validación para volver a escoger W.
19. **Stress Test independiente**: bandas extremas, mecanismos no vistos, sensibilidad del rendimiento y fidelidad de las condiciones respecto del diseño preregistrado.
20. **Real World externo e independiente**: manifiesto de datasets, ausencia de solapamiento o selección retrospectiva, comparación completa y límites de generalización.
21. **Incertidumbre y multiplicidad**: intervalos de confianza para MSE/Q95, dependencia jerárquica por semilla/familia/escenario, corrección por comparaciones múltiples y distinción entre exploración y confirmación.
22. **Controles negativos y recuperación near-gate**: diagnósticos de decisiones próximas al umbral y pruebas capaces de detectar falsos positivos o contaminación del protocolo.

### D. Integridad de ejecución
23. **Autonomía e independencia de etapas**: cada etapa debe poder ejecutarse, verificarse, publicarse y reanudarse por separado mediante el contrato común.
24. **Preservación de resultados y checkpointing**: trazabilidad, almacenamiento externo/versionado, límites de Actions, integridad de hashes y reglas de recuperación sin duplicar resultados.
25. **Gates científicos antes de deployment**: pruebas sintéticas, contratos de 321 escenarios, no mezcla 121/321, separación de datos, reproducibilidad, integridad de modelos y verificación de CI.
26. **Separación entre código y evidencia**: T3 conserva código, documentación y fixtures sintéticos mínimos; ninguna afirmación científica se considerará demostrada sin resultados de la nueva ejecución B3.

### Protocolo para desarrollar cada apartado
Para cada punto: **(i)** hipótesis o finalidad, **(ii)** definiciones y fórmulas, **(iii)** implementación y restricciones, **(iv)** supuestos y riesgos, **(v)** validaciones y criterios de aceptación, **(vi)** tablas/figuras previstas, **(vii)** estado de verificación. Este índice no autoriza un deployment completo: hace falta demostrar CI satisfactoria y revisar las rutas de producción.



## GitHub Actions-only stage exchange (30-day operational window)

Each stage writes outputs to its runner's working directory and **must upload** them with `actions/upload-artifact@v4` before its job ends. A runner's ephemeral disk does not persist across independent jobs. Set `retention-days: 30` and `if: always()` for diagnostics/checkpoints (while excluding secrets). A subsequent stage uses `actions/download-artifact@v4` with the specific producer run ID and artifact name, or the GitHub Actions artifact API, and validates stage/seed/manifest hashes before consumption. Artifacts are tied to workflow runs, not to Git commits or runner disks. Cross-run downloads may require `actions: read` on GITHUB_TOKEN. Do not depend on artifact availability after the configured retention interval.

The user's separate local backup workflow via Codex is intentionally **out of scope** for repository code: no automatic export, personal device credentials, or self-hosted runner configuration is required. Never assume local files can be fetched automatically by Actions.

Operational stages: Monte Carlo publishes a complete and verified dataset artifact; Discovery consumes that artifact and publishes frozen model artifacts; Held-out, Stress, and Real World consume frozen models independently (and their own applicable input datasets). No Azure OIDC, Key Vault, Blob Storage, or other third-party service is required. Each output includes role, seed index, family, sample size, source revision, SHA-256 and a completion marker. A final stage should only use artifacts marked complete. Large artifacts may need sharding and capacity checks.

**Status:** GitHub artifact exchange is the agreed contract. It must be wired and tested separately in every production workflow before claiming production readiness. The bounded statistical smoke succeeded in run 40224954621; it did not validate cross-run artifact injection.
