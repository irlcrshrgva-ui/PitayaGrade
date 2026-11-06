# PitayaGrade Browser Scan Check — 2026-11-06

## Test setup

- Build: local browser build served from this repository
- Scan mode: Photo Mode
- Quality model selected in the interface: ResNet50
- Object pipeline reported by the app: Dragon Fruit Presence Gate + YOLOv8-Nano + ResNet50 ONNX + HSV disease heuristics
- Browser: Codex in-app browser

## Red-skinned dragon fruit

- Test image: `dataset/public/quality/review/Fresh Dragon Fruit/row-0.jpg`
- SHA-256: `FDA7790507C6534ED20733AA2C78913AB379D21C7996B8F549A3A0B63F42FCA8`
- Object gate: accepted as dragon fruit
- Quality suggestion: Grade B
- Quality confidence: 41.1%
- Maturity estimate: Harvestable Stage, 80% readiness
- Processing time shown by the app: 3.2 seconds
- Harvest indicator: the new 70% marker was visible

## Yellow-skinned dragon fruit

- Test image: `dataset/grade-review-2026-11-06/variety-reference/yellow-dragon-fruit.jpg`
- SHA-256: `16F9C988DC24C0F0A8C2C33B273827FFE23FC1106803DBCA49FAF841C37CABE6`
- Object gate: rejected as unrecognized
- Object score: 20.8%
- Required score: 50%
- App message: yellow-skinned dragon fruit is not supported by the current models
- No quality, maturity, or disease result was issued, which is the safe behavior for an unrecognized image

## Interpretation

The browser scanner successfully completed an end-to-end scan of the red-skinned test image. This single check is functional evidence, not a model-accuracy measurement. The yellow-skinned variety is not yet supported and needs a representative, human-verified yellow-fruit dataset followed by retraining and held-out evaluation before it can be claimed as supported.

The 70% harvest marker is an app-level image estimate, not a biological guarantee. The interface tells users to confirm skin color, days after flowering, and field condition before harvesting.
