/* Evaluated model assets become selectable only after this registry is updated. */
const PitayaModelRegistry = Object.freeze([
  Object.freeze({
    id: 'dragonfruit-presence-gate',
    name: 'Dragon Fruit Presence Gate',
    role: 'object-presence-gate',
    available: true,
    status: 'bundled',
    modelPath: 'model/gate/dragonfruit-presence-gate.onnx',
    sha256: '2dfee37827b99ae3962fa6118b04a250137661661528f39c127a44de455639ff',
    inputSize: 160,
    preprocessing: 'rgb-imagenet-normalized',
    outputContract: 'binary-presence-logits-v1',
    threshold: 0.50,
    evaluation: Object.freeze({ sampleCount: 1476, accuracy: 0.9966124661,
      precision: 0.9783549784, recall: 1.0, specificity: 0.996, f1: 0.9890590810 }),
    classes: Object.freeze(['non-dragon-fruit', 'dragon-fruit'])
  }),
  Object.freeze({
    id: 'yolov8-nano',
    name: 'YOLOv8-Nano',
    role: 'integrated-detector-grader',
    available: true,
    status: 'bundled',
    modelPath: 'model/best.onnx',
    sha256: '3e4e7a138eecc1da53fc0f14c9400d100e79f61cf0aa2f971c8256a8afe4796a',
    inputSize: 640,
    preprocessing: 'rgb-zero-to-one',
    outputContract: 'yolov8-grade-detection-v1',
    cropGraderId: 'yolov8-nano-crop-grader',
    photoRecoveryGradeConfidence: .99,
    requiresVisualGate: true,
    evaluation: Object.freeze({"scope": "photo-scanner", "sampleCount": 147, "accuracy": 0.7482993197278912, "macroPrecision": 0.5927544677544677, "macroRecall": 0.5262382965871338, "macroF1": 0.5570761825392885}),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'yolov8-fruit-locator-negative-aware',
    name: 'YOLOv8 Fruit Locator (negative-aware candidate)',
    role: 'object-detector',
    selectable: false,
    available: true,
    status: 'bundled',
    modelPath: 'model/fruit-locator-negative-aware.onnx',
    sha256: '06200ddaf81af5d3005696db08445703a7e2a8c3a5a812ff9a12e6f9c62d6c41',
    inputSize: 416,
    preprocessing: 'rgb-zero-to-one',
    outputContract: 'yolov8-fruit-detection-v1',
    threshold: 0.50,
    evaluation: Object.freeze({ scope: 'object-detection', sampleCount: 51, map50: 0.9543, map5095: 0.6953 }),
    classes: Object.freeze(['dragon-fruit'])
  }),
  Object.freeze({
    id: 'yolov8-nano-crop-grader', name: 'YOLOv8-Nano crop grader', role: 'quality-classifier',
    selectable: false, available: true, status: 'bundled', modelPath: 'model/quality/yolov8-nano.onnx',
    sha256: 'dc8a46a56bffda2d86c509207931928bc82b6b731a1e0e60793a5126f960d726',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'mobilenetv2-quality', name: 'MobileNetV2', role: 'quality-classifier',
    photoRecoveryGradeConfidence: .7,
    available: true, status: 'bundled', modelPath: 'model/quality/mobilenetv2.onnx',
    sha256: '413d6e17b2a6c7ff108665b00e25041d2f1f4956eb127599188366e4e8bb4665',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({"scope": "photo-scanner", "sampleCount": 147, "accuracy": 0.7755102040816326, "macroPrecision": 0.6347222222222222, "macroRecall": 0.5605934762911506, "macroF1": 0.5932280982638715}),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'resnet50-quality', name: 'ResNet50', role: 'quality-classifier',
    photoRecoveryGradeConfidence: .6,
    available: true, status: 'bundled', modelPath: 'model/quality/resnet50.onnx',
    sha256: 'b87a808465b27203a9ce735f0840ce1d03e6ada2d1cc2f4a9a110548866a5673',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({"scope": "photo-scanner", "sampleCount": 147, "accuracy": 0.7687074829931972, "macroPrecision": 0.5942434210526316, "macroRecall": 0.5209528843249773, "macroF1": 0.5540893733664818}),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'efficientnet-b3-quality', name: 'EfficientNet-B3 v7 (full-frame)', role: 'quality-classifier',
    photoRecoveryGradeConfidence: .9,
    inferenceMode: 'full-frame-when-fruit-verified',
    available: true, status: 'bundled', modelPath: 'model/quality/efficientnet-b3.onnx',
    sha256: '89046c5a92df279b7cd81f3251d0de102b4742db9fa2cb72728bbd63344c722a',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({ scope: 'direct-classifier-development-test', sampleCount: 198, accuracy: 0.8686868686868687,
      macroPrecision: 0.8100961538461539, macroRecall: 0.844642857142857, macroF1: 0.8193234346848299,
      perClassRecall: Object.freeze({ 'Grade A': 0.8571428571428571, 'Grade B': 0.7142857142857143,
        'Grade C': 0.8571428571428571, 'Reject': 0.95 }),
      note: 'V7 development test, full-frame classifier only; 84/198 images overlap prior app training IDs; not fresh orchard validation or full-scanner accuracy.' }),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'yolov8n-disease-seg', name: 'YOLOv8-Nano Disease Segmentation',
    role: 'disease-segmenter', available: false,
    status: 'awaiting-evaluated-export', modelPath: null, sha256: null,
    inputSize: 128, preprocessing: 'rgb-zero-to-one', outputContract: 'yolov8-disease-segmentation-v1',
    classes: Object.freeze(['Anthracnose', 'Stem Canker', 'Soft Rot',
      'Pest Damage', 'Sunburn', 'Fungal Spots'])
  })
]);
