import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/app_theme.dart';
import '../services/ml_service.dart';
import '../services/database_service.dart';
import '../services/notification_service.dart';
import '../models/scan_result.dart';
import '../widgets/grade_badge.dart';

class ScanScreen extends StatefulWidget {
  final NotificationService notifService;
  const ScanScreen({super.key, required this.notifService});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _imageBytes;
  bool _isProcessing = false;
  ScanResult? _result;
  int _processingStep = -1;

  final _steps = [
    'Resizing image...',
    'Normalizing colors...',
    'Segmenting fruit...',
    'Quality grading...',
    'Disease detection...',
    'Generating results...',
  ];

  Future<void> _pickImage(ImageSource source) async {
    final file = await _picker.pickImage(source: source, imageQuality: 85, maxWidth: 1024);
    if (file != null) {
      final bytes = await file.readAsBytes();
      setState(() {
        _imageBytes = bytes;
        _result = null;
      });
    }
  }

  Future<void> _analyze() async {
    if (_imageBytes == null || _isProcessing) return;

    setState(() {
      _isProcessing = true;
      _processingStep = 0;
      _result = null;
    });

    // Animate through processing steps
    for (int i = 0; i < _steps.length; i++) {
      setState(() => _processingStep = i);
      await Future.delayed(Duration(milliseconds: 250 + (i == 3 || i == 4 ? 400 : 100)));
    }

    // Run ML inference
    final result = await MLService.analyzeImage(_imageBytes!);

    // Save to database
    await DatabaseService.insertScan(result);

    // Generate notifications
    widget.notifService.generateScanAlert(
      gradeLabel: result.grade.label,
      gradeConfidence: result.grade.confidence,
      diseaseName: result.disease.name,
      diseaseConfidence: result.disease.confidence,
      isHealthy: result.disease.isHealthy,
    );

    setState(() {
      _result = result;
      _isProcessing = false;
      _processingStep = -1;
    });
  }

  void _reset() {
    setState(() {
      _imageBytes = null;
      _result = null;
      _isProcessing = false;
      _processingStep = -1;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Scan Fruit', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        const Text('Capture or upload a dragon fruit image', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
        const SizedBox(height: 16),

        // Scanner Zone
        _buildScannerZone(),
        const SizedBox(height: 16),

        // Buttons
        if (_imageBytes == null) ...[
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _pickImage(ImageSource.camera),
                  icon: const Text('📷'),
                  label: const Text('Capture Photo'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 52,
                child: ElevatedButton(
                  onPressed: () => _pickImage(ImageSource.gallery),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.bgElevated,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('📁'),
                ),
              ),
            ],
          ),
        ] else if (_result == null) ...[
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _isProcessing ? null : _analyze,
              icon: const Text('🔬'),
              label: Text(_isProcessing ? 'Analyzing...' : 'Analyze Dragon Fruit'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.success,
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ),
        ],

        // Results
        if (_result != null) ...[
          const SizedBox(height: 16),
          _buildResultCard(_result!),
        ],

        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildScannerZone() {
    return GestureDetector(
      onTap: _imageBytes == null && !_isProcessing ? () => _pickImage(ImageSource.camera) : null,
      child: AspectRatio(
        aspectRatio: 1,
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(24),
            border: _imageBytes == null
                ? Border.all(color: Colors.white.withOpacity(0.12), width: 2, strokeAlign: BorderSide.strokeAlignInside)
                : null,
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Placeholder or image
              if (_imageBytes == null)
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const [
                    Text('📸', style: TextStyle(fontSize: 56)),
                    SizedBox(height: 16),
                    Text('Tap to capture or upload', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: AppColors.textSecondary)),
                    SizedBox(height: 4),
                    Text('JPG, PNG - best results with good lighting', style: TextStyle(fontSize: 12, color: AppColors.textTertiary)),
                  ],
                )
              else
                Image.memory(_imageBytes!, fit: BoxFit.cover),

              // Frame guide overlay
              if (_imageBytes != null && !_isProcessing && _result == null)
                CustomPaint(painter: _FrameGuidePainter()),

              // Processing overlay
              if (_isProcessing)
                Container(
                  color: AppColors.bgApp.withOpacity(0.85),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(
                        width: 56,
                        height: 56,
                        child: CircularProgressIndicator(
                          strokeWidth: 3,
                          valueColor: AlwaysStoppedAnimation(AppColors.primary),
                        ),
                      ),
                      const SizedBox(height: 24),
                      ..._steps.asMap().entries.map((entry) {
                        final i = entry.key;
                        final text = entry.value;
                        final isDone = i < _processingStep;
                        final isActive = i == _processingStep;
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Text(
                            '${isDone ? '✅' : isActive ? '⏳' : '⬜'} $text',
                            style: TextStyle(
                              fontSize: 12,
                              color: isActive ? AppColors.primary : isDone ? AppColors.success : AppColors.textTertiary,
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResultCard(ScanResult result) {
    final gradeColor = AppColors.gradeColor(result.grade.label);
    final confPct = (result.grade.confidence * 100).toStringAsFixed(1);
    final diseaseConfPct = (result.disease.confidence * 100).toStringAsFixed(1);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        children: [
          // Grade Header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 28),
            decoration: BoxDecoration(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              gradient: LinearGradient(
                colors: [gradeColor.withOpacity(0.15), Colors.transparent],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
            child: Column(
              children: [
                Text(
                  'QUALITY GRADE',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 1.5, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 8),
                Text(
                  result.grade.label,
                  style: TextStyle(fontSize: 36, fontWeight: FontWeight.w700, color: gradeColor),
                ),
                const SizedBox(height: 4),
                Text('$confPct% confidence', style: const TextStyle(fontSize: 14, color: AppColors.textSecondary)),
                const SizedBox(height: 8),
                SizedBox(
                  width: 180,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: result.grade.confidence,
                      minHeight: 6,
                      backgroundColor: Colors.white.withOpacity(0.1),
                      valueColor: AlwaysStoppedAnimation(
                        result.grade.confidence > 0.85 ? AppColors.success : result.grade.confidence > 0.7 ? AppColors.warning : AppColors.error,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Disease Status
                _sectionTitle('Disease Detection'),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    color: result.disease.isHealthy
                        ? AppColors.success.withOpacity(0.1)
                        : result.disease.confidence > 0.8
                            ? AppColors.error.withOpacity(0.1)
                            : AppColors.warning.withOpacity(0.1),
                    border: Border.all(
                      color: (result.disease.isHealthy ? AppColors.success : result.disease.confidence > 0.8 ? AppColors.error : AppColors.warning).withOpacity(0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      Text(result.disease.isHealthy ? '✅' : '⚠️', style: const TextStyle(fontSize: 18)),
                      const SizedBox(width: 10),
                      Expanded(child: Text(result.disease.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
                      Text('$diseaseConfPct%', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Details
                _sectionTitle('Assessment Details'),
                const SizedBox(height: 8),
                _detailRow('📏 Size', result.details.size),
                _detailRow('🎨 Color Uniformity', result.details.colorUniformity),
                _detailRow('🔬 Surface', result.details.surfaceCondition),
                _detailRow('📶 Mode', result.details.processingMode),
                _detailRow('⚡ Time', result.details.processingTime),
                const SizedBox(height: 20),

                // Recommendations
                _sectionTitle('Recommendations'),
                const SizedBox(height: 8),
                ...result.recommendations.map((r) => _recommendationCard(r)),
                const SizedBox(height: 16),

                // Scan Another
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _reset,
                    icon: const Text('📷'),
                    label: const Text('Scan Another'),
                    style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Text(
      text.toUpperCase(),
      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 1, color: AppColors.textTertiary),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _recommendationCard(Recommendation rec) {
    final color = rec.type == RecommendationType.positive
        ? AppColors.success
        : rec.type == RecommendationType.warning
            ? AppColors.warning
            : AppColors.error;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: color.withOpacity(0.08),
        border: Border.all(color: color.withOpacity(0.15)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(rec.icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(rec.text, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.5)),
          ),
        ],
      ),
    );
  }
}

class _FrameGuidePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.4)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final accentPaint = Paint()
      ..color = AppColors.primary
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final rect = Rect.fromCenter(
      center: Offset(size.width / 2, size.height / 2),
      width: size.width * 0.7,
      height: size.height * 0.7,
    );

    canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(20)), paint);

    const cornerLen = 30.0;
    // Top-left corner
    canvas.drawLine(rect.topLeft + const Offset(0, 10), rect.topLeft + Offset(0, cornerLen), accentPaint);
    canvas.drawLine(rect.topLeft + const Offset(10, 0), rect.topLeft + Offset(cornerLen, 0), accentPaint);
    // Bottom-right corner
    canvas.drawLine(rect.bottomRight - const Offset(0, 10), rect.bottomRight - Offset(0, cornerLen), accentPaint);
    canvas.drawLine(rect.bottomRight - const Offset(10, 0), rect.bottomRight - Offset(cornerLen, 0), accentPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
