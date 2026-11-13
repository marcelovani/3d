# Models

One folder per model. Each has a `NOTES.md` with the decisions and history, and, where the model is generated, a `build.sh` that rebuilds it from scratch.

| Model | What it is |
|-------|------------|
| [Engine/](Engine/) | A 15 cm printable car engine with a motor-driven flywheel and fan, and a smoke system blowing through the exhaust. Based on "Internal Combustion Engine" by T-FLEX CAD ST (Free), CC BY 3.0 ([credits](Engine/source/ATTRIBUTION.md)) |

Build outputs (`output/`) and intermediates (`work/`) are not committed. Source models are committed only when their licence allows it, with a `source/ATTRIBUTION.md`. Run the model's `build.sh` to regenerate them.
