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
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'mobilenetv2-quality', name: 'MobileNetV2', role: 'quality-classifier',
    available: false, status: 'awaiting-evaluated-export', modelPath: null,
    sha256: null, inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'resnet50-quality', name: 'ResNet50', role: 'quality-classifier',
    available: false, status: 'awaiting-evaluated-export', modelPath: null,
    sha256: null, inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
    classes: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject'])
  }),
  Object.freeze({
    id: 'efficientnet-b3-quality', name: 'EfficientNet-B3', role: 'quality-classifier',
    available: false, status: 'awaiting-evaluated-export', modelPath: null,
    sha256: null, inputSize: 224, preprocessing: 'rgb-imagenet-normalized', outputContract: 'quality-softmax-v1',
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
