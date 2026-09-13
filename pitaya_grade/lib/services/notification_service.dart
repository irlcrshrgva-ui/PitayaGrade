import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class NotificationItem {
  final String id;
  final String title;
  final String body;
  final String severity; // low, medium, high, success
  final String icon;
  final DateTime time;
  bool read;

  NotificationItem({
    required this.id,
    required this.title,
    required this.body,
    required this.severity,
    required this.icon,
    required this.time,
    this.read = false,
  });
}

class NotificationService extends ChangeNotifier {
  final List<NotificationItem> _notifications = [];

  List<NotificationItem> get notifications => List.unmodifiable(_notifications);
  int get unreadCount => _notifications.where((n) => !n.read).length;

  void add({
    required String title,
    required String body,
    String severity = 'low',
    String icon = '🔔',
  }) {
    _notifications.insert(0, NotificationItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title,
      body: body,
      severity: severity,
      icon: icon,
      time: DateTime.now(),
    ));

    if (_notifications.length > 50) {
      _notifications.removeLast();
    }
    notifyListeners();
  }

  void markAllRead() {
    for (final n in _notifications) {
      n.read = true;
    }
    notifyListeners();
  }

  void clearAll() {
    _notifications.clear();
    notifyListeners();
  }

  void generateScanAlert({
    required String gradeLabel,
    required double gradeConfidence,
    required String diseaseName,
    required double diseaseConfidence,
    required bool isHealthy,
  }) {
    // Disease alert
    if (!isHealthy) {
      final severity = diseaseConfidence > 0.85 ? 'high' : diseaseConfidence > 0.65 ? 'medium' : 'low';
      final advice = _getDiseaseAdvice(diseaseName);
      add(
        title: '$diseaseName Detected',
        body: 'Detected with ${(diseaseConfidence * 100).toStringAsFixed(1)}% confidence. $advice',
        severity: severity,
        icon: severity == 'high' ? '🚨' : '⚠️',
      );
    }

    // Reject alert
    if (gradeLabel == 'Reject') {
      add(
        title: 'Fruit Rejected',
        body: 'Classified as Reject with ${(gradeConfidence * 100).toStringAsFixed(1)}% confidence.',
        severity: 'high',
        icon: '❌',
      );
    }

    // Premium celebration
    if (gradeLabel == 'Grade A' && gradeConfidence > 0.9) {
      add(
        title: 'Premium Quality!',
        body: 'Grade A fruit with ${(gradeConfidence * 100).toStringAsFixed(1)}% confidence. Ready for premium market.',
        severity: 'success',
        icon: '🌟',
      );
    }
  }

  String _getDiseaseAdvice(String name) {
    const advice = {
      'Anthracnose': 'Apply copper-based fungicide. Monitor nearby fruits.',
      'Stem Canker': 'Isolate affected area. Consult agricultural officer.',
      'Soft Rot': 'Remove affected fruit immediately to prevent spread.',
      'Pest Damage': 'Inspect for pest colonies. Consider pest management.',
      'Sunburn': 'Provide shade protection for exposed fruits.',
      'Fungal Spots': 'Apply appropriate fungicide treatment.',
    };
    return advice[name] ?? 'Monitor closely and consult an expert.';
  }

  Color severityColor(String severity) {
    switch (severity) {
      case 'high': return const Color(0xFFEF4444);
      case 'medium': return const Color(0xFFF59E0B);
      case 'success': return const Color(0xFF22C55E);
      default: return const Color(0xFF3B82F6);
    }
  }

  String timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inSeconds < 60) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}
