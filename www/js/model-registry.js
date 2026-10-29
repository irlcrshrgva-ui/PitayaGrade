/* Evaluated model assets become selectable only after this registry is updated. */
const PitayaModelRegistry = Object.freeze([
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
    requiresVisualGate: true,
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'mobilenetv2-quality', name: 'MobileNetV2', role: 'quality-classifier',
    available: true, status: 'bundled', modelPath: 'model/quality/mobilenetv2.onnx',
    sha256: '72b2dab116a59cf5e45ddff0408e256c019683d5880e897e504fbf32e110f971',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({ sampleCount: 226, accuracy: 0.7212389381,
      macroPrecision: 0.5694608840, macroRecall: 0.5607253936, macroF1: 0.5531378247 }),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'resnet50-quality', name: 'ResNet50', role: 'quality-classifier',
    available: true, status: 'bundled', modelPath: 'model/quality/resnet50.onnx',
    sha256: 'b87a808465b27203a9ce735f0840ce1d03e6ada2d1cc2f4a9a110548866a5673',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({ sampleCount: 226, accuracy: 0.7433628319,
      macroPrecision: 0.5775401069, macroRecall: 0.5483870371, macroF1: 0.5483229556 }),
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'efficientnet-b3-quality', name: 'EfficientNet-B3', role: 'quality-classifier',
    available: true, status: 'bundled', modelPath: 'model/quality/efficientnet-b3.onnx',
    sha256: '8461dc36ee59e26111ea7a205095db44e5bc0d77114a1c75258761a262c2b390',
    inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    evaluation: Object.freeze({ sampleCount: 226, accuracy: 0.7256637168,
      macroPrecision: 0.5941570110, macroRecall: 0.5722070517, macroF1: 0.5780325491 }),
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
