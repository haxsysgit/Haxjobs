# CV Variants

This directory is the source map for reusable HaxJobs CV variants.

Per-job packs should reference one of these variants. They should not create new `Tailored_CV` files by default.

The registry lives at:

```text
cv_variants/registry.json
```

Each variant directory can contain the approved HTML/PDF once generated or promoted from an older pack:

```text
cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.pdf
cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.html
```

Files are generated locally.

```bash
scripts/pull-cv-variants
```
