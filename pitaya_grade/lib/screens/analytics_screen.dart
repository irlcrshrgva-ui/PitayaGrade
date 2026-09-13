import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme/app_theme.dart';
import '../services/database_service.dart';
import '../models/scan_result.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  List<ScanResult> _scans = [];
  Map<String, int> _gradeDistribution = {};
  Map<String, int> _diseaseDistribution = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final scans = await DatabaseService.getAllScans();
    final gradeDist = await DatabaseService.getGradeDistribution();
    final diseaseDist = await DatabaseService.getDiseaseDistribution();

    if (mounted) {
      setState(() {
        _scans = scans;
        _gradeDistribution = gradeDist;
        _diseaseDistribution = diseaseDist;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final total = _scans.length;
    final premiumCount = _scans.where((s) => s.grade.label == 'Grade A').length;

    return RefreshIndicator(
      color: AppColors.primary,
      backgroundColor: AppColors.bgCard,
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Analytics', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Deep insights into your farm data', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
          const SizedBox(height: 20),

          // Summary Stats
          Row(
            children: [
              Expanded(child: _statMini('📊', 'Total Scans', '$total', AppColors.primary)),
              const SizedBox(width: 12),
              Expanded(child: _statMini('⭐', 'Premium', total > 0 ? '${((premiumCount / total) * 100).toStringAsFixed(0)}%' : '0%', AppColors.success)),
            ],
          ),
          const SizedBox(height: 24),

          // Disease Trend Chart
          _chartCard('Disease Trend (Last 7 Days)', _buildDiseaseTrendChart()),
          const SizedBox(height: 16),

          // Quality Over Time Chart
          _chartCard('Quality Over Time', _buildQualityChart()),
          const SizedBox(height: 16),

          // Disease Breakdown
          _chartCard('Disease Breakdown', _buildDiseaseBreakdown()),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _statMini(String icon, String label, String value, Color accent) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: accent.withOpacity(0.15),
            ),
            child: Text(icon, style: const TextStyle(fontSize: 18)),
          ),
          const SizedBox(height: 10),
          Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ],
      ),
    );
  }

  Widget _chartCard(String title, Widget chart) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          chart,
        ],
      ),
    );
  }

  Widget _buildDiseaseTrendChart() {
    // Group scans by day for last 7 days
    final now = DateTime.now();
    final days = List.generate(7, (i) {
      final d = now.subtract(Duration(days: 6 - i));
      return DateTime(d.year, d.month, d.day);
    });

    final healthyData = <FlSpot>[];
    final diseasedData = <FlSpot>[];

    for (int i = 0; i < days.length; i++) {
      final day = days[i];
      final dayScans = _scans.where((s) {
        final sd = DateTime(s.timestamp.year, s.timestamp.month, s.timestamp.day);
        return sd == day;
      });
      healthyData.add(FlSpot(i.toDouble(), dayScans.where((s) => s.disease.isHealthy).length.toDouble()));
      diseasedData.add(FlSpot(i.toDouble(), dayScans.where((s) => !s.disease.isHealthy).length.toDouble()));
    }

    if (_scans.isEmpty) {
      return const SizedBox(
        height: 180,
        child: Center(child: Text('No data yet', style: TextStyle(color: AppColors.textTertiary))),
      );
    }

    return SizedBox(
      height: 200,
      child: BarChart(
        BarChartData(
          barGroups: List.generate(7, (i) {
            return BarChartGroupData(
              x: i,
              barRods: [
                BarChartRodData(
                  toY: healthyData[i].y,
                  color: AppColors.success,
                  width: 10,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
                ),
                BarChartRodData(
                  toY: diseasedData[i].y,
                  color: AppColors.error,
                  width: 10,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
                ),
              ],
            );
          }),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                getTitlesWidget: (v, _) => Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: AppColors.textTertiary)),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  final d = days[v.toInt()];
                  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                  return Text(weekdays[d.weekday - 1], style: const TextStyle(fontSize: 10, color: AppColors.textTertiary));
                },
              ),
            ),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(color: Colors.white.withOpacity(0.04), strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }

  Widget _buildQualityChart() {
    if (_scans.isEmpty) {
      return const SizedBox(
        height: 180,
        child: Center(child: Text('No data yet', style: TextStyle(color: AppColors.textTertiary))),
      );
    }

    final now = DateTime.now();
    final days = List.generate(7, (i) {
      final d = now.subtract(Duration(days: 6 - i));
      return DateTime(d.year, d.month, d.day);
    });

    final gradeMap = {'Grade A': 4.0, 'Grade B': 3.0, 'Grade C': 2.0, 'Reject': 1.0};

    final spots = <FlSpot>[];
    for (int i = 0; i < days.length; i++) {
      final day = days[i];
      final dayScans = _scans.where((s) {
        final sd = DateTime(s.timestamp.year, s.timestamp.month, s.timestamp.day);
        return sd == day;
      }).toList();

      if (dayScans.isNotEmpty) {
        final avg = dayScans.map((s) => gradeMap[s.grade.label] ?? 2.0).reduce((a, b) => a + b) / dayScans.length;
        spots.add(FlSpot(i.toDouble(), avg));
      }
    }

    return SizedBox(
      height: 200,
      child: LineChart(
        LineChartData(
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              color: AppColors.primary,
              barWidth: 3,
              dotData: FlDotData(
                show: true,
                getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                  radius: 4, strokeWidth: 2, strokeColor: AppColors.primary, color: Colors.white,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [AppColors.primary.withOpacity(0.2), AppColors.primary.withOpacity(0.0)],
                ),
              ),
            ),
          ],
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                interval: 1,
                getTitlesWidget: (v, _) {
                  const labels = {1: 'R', 2: 'C', 3: 'B', 4: 'A'};
                  return Text(labels[v.toInt()] ?? '', style: const TextStyle(fontSize: 10, color: AppColors.textTertiary));
                },
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  if (v.toInt() >= days.length) return const SizedBox();
                  final d = days[v.toInt()];
                  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                  return Text(weekdays[d.weekday - 1], style: const TextStyle(fontSize: 10, color: AppColors.textTertiary));
                },
              ),
            ),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          minY: 0, maxY: 5,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(color: Colors.white.withOpacity(0.04), strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }

  Widget _buildDiseaseBreakdown() {
    if (_diseaseDistribution.isEmpty) {
      return const SizedBox(
        height: 120,
        child: Center(child: Text('No disease data', style: TextStyle(color: AppColors.textTertiary))),
      );
    }

    final colors = {
      'Anthracnose': const Color(0xFFEF4444),
      'Stem Canker': const Color(0xFFF97316),
      'Soft Rot': const Color(0xFFA855F7),
      'Pest Damage': const Color(0xFFF59E0B),
      'Sunburn': const Color(0xFFEC4899),
      'Fungal Spots': const Color(0xFF6366F1),
    };

    final total = _diseaseDistribution.values.fold<int>(0, (a, b) => a + b);
    final sorted = _diseaseDistribution.entries.toList()..sort((a, b) => b.value.compareTo(a.value));

    return Column(
      children: sorted.map((entry) {
        final pct = total > 0 ? entry.value / total : 0.0;
        final color = colors[entry.key] ?? AppColors.textTertiary;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
              const SizedBox(width: 8),
              SizedBox(width: 90, child: Text(entry.key, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: pct,
                    minHeight: 6,
                    backgroundColor: Colors.white.withOpacity(0.06),
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 50,
                child: Text(
                  '${entry.value} (${(pct * 100).toStringAsFixed(0)}%)',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                  textAlign: TextAlign.right,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
