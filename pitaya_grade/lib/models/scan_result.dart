import 'dart:typed_data';

class ScanResult {
  final String id;
  final DateTime timestamp;
  final Uint8List? thumbnail;
  final String? imagePath;
  final GradeResult grade;
  final DiseaseResult disease;
  final ScanDetails details;
  final List<Recommendation> recommendations;
  String notes;

  ScanResult({
    required this.id,
    required this.timestamp,
    this.thumbnail,
    this.imagePath,
    required this.grade,
    required this.disease,
    required this.details,
    required this.recommendations,
    this.notes = '',
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'timestamp': timestamp.toIso8601String(),
      'imagePath': imagePath,
      'gradeLabel': grade.label,
      'gradeConfidence': grade.confidence,
      'diseaseName': disease.name,
      'diseaseConfidence': disease.confidence,
      'diseaseIsHealthy': disease.isHealthy ? 1 : 0,
      'detailsSize': details.size,
      'detailsColorUniformity': details.colorUniformity,
      'detailsSurfaceCondition': details.surfaceCondition,
      'detailsProcessingMode': details.processingMode,
      'detailsProcessingTime': details.processingTime,
      'notes': notes,
    };
  }

  factory ScanResult.fromMap(Map<String, dynamic> map) {
    final gradeLabel = map['gradeLabel'] as String;
    return ScanResult(
      id: map['id'] as String,
      timestamp: DateTime.parse(map['timestamp'] as String),
      imagePath: map['imagePath'] as String?,
      grade: GradeResult(
        label: gradeLabel,
        confidence: (map['gradeConfidence'] as num).toDouble(),
      ),
      disease: DiseaseResult(
        name: map['diseaseName'] as String,
        confidence: (map['diseaseConfidence'] as num).toDouble(),
        isHealthy: (map['diseaseIsHealthy'] as int) == 1,
      ),
      details: ScanDetails(
        size: map['detailsSize'] as String,
        colorUniformity: map['detailsColorUniformity'] as String,
        surfaceCondition: map['detailsSurfaceCondition'] as String,
        processingMode: map['detailsProcessingMode'] as String,
        processingTime: map['detailsProcessingTime'] as String,
      ),
      recommendations: _getRecommendations(gradeLabel, map['diseaseName'] as String),
      notes: map['notes'] as String? ?? '',
    );
  }

  static List<Recommendation> _getRecommendations(String grade, String disease) {
    final recs = <Recommendation>[];

    switch (grade) {
      case 'Grade A':
        recs.add(Recommendation(
          type: RecommendationType.positive,
          icon: '🌟',
          text: 'Premium quality. Ready for premium market or export. Harvest at peak maturity.',
        ));
        break;
      case 'Grade B':
        recs.add(Recommendation(
          type: RecommendationType.positive,
          icon: '✅',
          text: 'Standard quality. Suitable for domestic retail market. Consider allowing more ripening time.',
        ));
        break;
      case 'Grade C':
        recs.add(Recommendation(
          type: RecommendationType.warning,
          icon: '⚠️',
          text: 'Economy grade. Best suited for processing or local market. Monitor for further degradation.',
        ));
        break;
      case 'Reject':
        recs.add(Recommendation(
          type: RecommendationType.critical,
          icon: '❌',
          text: 'Not suitable for market sale. Remove from harvest batch to prevent quality contamination.',
        ));
        break;
    }

    if (disease != 'Healthy') {
      final diseaseAdvice = <String, String>{
        'Anthracnose': 'Anthracnose detected. Apply copper-based fungicide immediately. Isolate from healthy fruits.',
        'Stem Canker': 'Stem canker identified. Prune affected cladodes. Apply Mancozeb fungicide.',
        'Soft Rot': 'Bacterial soft rot present. Remove and destroy affected fruit immediately.',
        'Pest Damage': 'Pest damage observed. Inspect for mealybugs or scale insects. Apply appropriate insecticide.',
        'Sunburn': 'Sunburn damage detected. Install shade netting (30-50%) over exposed areas.',
        'Fungal Spots': 'Fungal spots present. Apply preventive fungicide. Ensure proper spacing for airflow.',
      };

      recs.add(Recommendation(
        type: RecommendationType.critical,
        icon: '🦠',
        text: diseaseAdvice[disease] ?? 'Disease detected. Consult agricultural extension officer.',
      ));
    } else {
      recs.add(Recommendation(
        type: RecommendationType.positive,
        icon: '🛡️',
        text: 'No disease detected. Fruit appears healthy. Continue regular monitoring.',
      ));
    }

    return recs;
  }
}

class GradeResult {
  final String label;
  final double confidence;

  GradeResult({required this.label, required this.confidence});

  String get shortLabel {
    switch (label) {
      case 'Grade A': return 'A';
      case 'Grade B': return 'B';
      case 'Grade C': return 'C';
      case 'Reject': return 'R';
      default: return '?';
    }
  }
}

class DiseaseResult {
  final String name;
  final double confidence;
  final bool isHealthy;

  DiseaseResult({
    required this.name,
    required this.confidence,
    required this.isHealthy,
  });
}

class ScanDetails {
  final String size;
  final String colorUniformity;
  final String surfaceCondition;
  final String processingMode;
  final String processingTime;

  ScanDetails({
    required this.size,
    required this.colorUniformity,
    required this.surfaceCondition,
    required this.processingMode,
    required this.processingTime,
  });
}

enum RecommendationType { positive, warning, critical }

class Recommendation {
  final RecommendationType type;
  final String icon;
  final String text;

  Recommendation({required this.type, required this.icon, required this.text});
}
