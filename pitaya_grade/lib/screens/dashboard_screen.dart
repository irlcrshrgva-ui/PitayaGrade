import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/database_service.dart';
import '../services/notification_service.dart';
import '../models/scan_result.dart';
import '../widgets/stat_card.dart';
import '../widgets/grade_badge.dart';

class DashboardScreen extends StatefulWidget {
  final NotificationService notifService;
  const DashboardScreen({super.key, required this.notifService});

  @override
  State<DashboardScreen> createState() => DashboardScreenState();
}

class DashboardScreenState extends State<DashboardScreen> {
  List<ScanResult> _scans = [];
  Map<String, int> _gradeDistribution = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final scans = await DatabaseService.getAllScans();
    final gradeDist = await DatabaseService.getGradeDistribution();
    if (mounted) {
      setState(() {
        _scans = scans;
        _gradeDistribution = gradeDist;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: AppColors.primary,
      backgroundColor: AppColors.bgCard,
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Header
          const Text(
            'Dashboard',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          const Text(
            'Your farm overview at a glance',
            style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 20),

          // Stats Grid
          _buildStatsGrid(),
          const SizedBox(height: 24),

          // Quick Actions
          _sectionHeader('Quick Actions', null),
          const SizedBox(height: 12),
          _buildQuickActions(),
          const SizedBox(height: 24),

          // Harvest Readiness
          _buildHarvestGauge(),
          const SizedBox(height: 24),

          // Grade Distribution
          _buildGradeDistribution(),
          const SizedBox(height: 24),

          // Recent Scans
          _sectionHeader('Recent Scans', null),
          const SizedBox(height: 12),
          _buildRecentScans(),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildStatsGrid() {
    final total = _scans.length;
    final diseased = _scans.where((s) => !s.disease.isHealthy).length;
    final healthy = total - diseased;

    String avgGrade = '--';
    if (total > 0) {
      final gradeMap = {'Grade A': 4, 'Grade B': 3, 'Grade C': 2, 'Reject': 1};
      final avg = _scans.map((s) => gradeMap[s.grade.label] ?? 2).reduce((a, b) => a + b) / total;
      avgGrade = avg > 3.5 ? 'A' : avg > 2.5 ? 'B' : avg > 1.5 ? 'C' : 'R';
    }

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        StatCard(icon: '📊', value: '$total', label: 'Total Scans', accentColor: AppColors.primary),
        StatCard(icon: '✅', value: avgGrade, label: 'Avg. Grade', accentColor: AppColors.success),
        StatCard(
          icon: '🦠',
          value: total > 0 ? '${((diseased / total) * 100).toStringAsFixed(0)}%' : '0%',
          label: 'Disease Rate',
          accentColor: AppColors.warning,
        ),
        StatCard(
          icon: '🌿',
          value: total > 0 ? '${((healthy / total) * 100).toStringAsFixed(0)}%' : '0%',
          label: 'Healthy Rate',
          accentColor: AppColors.info,
        ),
      ],
    );
  }

  Widget _buildQuickActions() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      childAspectRatio: 2.2,
      children: [
        _quickActionBtn('📸', 'New Scan', () {}),
        _quickActionBtn('📄', 'Export Report', () {}),
        _quickActionBtn('📋', 'View History', () {}),
        _quickActionBtn('📈', 'Analytics', () {}),
      ],
    );
  }

  Widget _quickActionBtn(String icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(icon, style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }

  Widget _buildHarvestGauge() {
    double readiness = 0;
    if (_scans.isNotEmpty) {
      final gradeMap = {'Grade A': 100, 'Grade B': 75, 'Grade C': 50, 'Reject': 10};
      readiness = _scans.map((s) => gradeMap[s.grade.label] ?? 50).reduce((a, b) => a + b) / _scans.length;
    }

    final color = readiness > 70 ? AppColors.success : readiness > 40 ? AppColors.warning : AppColors.error;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        children: [
          const Text('Harvest Readiness', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          SizedBox(
            width: 140,
            height: 140,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CircularProgressIndicator(
                    value: readiness / 100,
                    strokeWidth: 10,
                    backgroundColor: Colors.white.withOpacity(0.06),
                    valueColor: AlwaysStoppedAnimation(color),
                    strokeCap: StrokeCap.round,
                  ),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '${readiness.toStringAsFixed(0)}%',
                      style: TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: color),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Based on recent scan quality distribution',
            style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }

  Widget _buildGradeDistribution() {
    final total = _gradeDistribution.values.fold<int>(0, (a, b) => a + b);

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
          const Text('Grade Distribution', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          if (total == 0)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No data yet', style: TextStyle(color: AppColors.textTertiary)),
              ),
            )
          else
            ...['Grade A', 'Grade B', 'Grade C', 'Reject'].map((grade) {
              final count = _gradeDistribution[grade] ?? 0;
              final pct = total > 0 ? count / total : 0.0;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    SizedBox(
                      width: 60,
                      child: Text(
                        grade.replaceAll('Grade ', ''),
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.gradeColor(grade),
                        ),
                      ),
                    ),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: pct,
                          minHeight: 8,
                          backgroundColor: Colors.white.withOpacity(0.06),
                          valueColor: AlwaysStoppedAnimation(AppColors.gradeColor(grade)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      width: 40,
                      child: Text(
                        '${(pct * 100).toStringAsFixed(0)}%',
                        textAlign: TextAlign.right,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildRecentScans() {
    if (_scans.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(40),
        child: Column(
          children: const [
            Text('📷', style: TextStyle(fontSize: 48)),
            SizedBox(height: 12),
            Text('No scans yet', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
            SizedBox(height: 4),
            Text('Start scanning dragon fruit to see results here.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: AppColors.textTertiary)),
          ],
        ),
      );
    }

    return Column(
      children: _scans.take(5).map((scan) => _buildScanItem(scan)).toList(),
    );
  }

  Widget _buildScanItem(ScanResult scan) {
    final time = '${scan.timestamp.day}/${scan.timestamp.month} ${scan.timestamp.hour.toString().padLeft(2, '0')}:${scan.timestamp.minute.toString().padLeft(2, '0')}';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Row(
        children: [
          // Thumbnail
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: AppColors.bgElevated,
            ),
            child: scan.thumbnail != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.memory(scan.thumbnail!, fit: BoxFit.cover),
                  )
                : const Center(child: Text('🐉', style: TextStyle(fontSize: 24))),
          ),
          const SizedBox(width: 12),
          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${scan.grade.label}${!scan.disease.isHealthy ? ' - ${scan.disease.name}' : ''}',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  '$time | ${scan.details.processingTime}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          // Grade badge
          GradeBadge(grade: scan.grade.label),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title, VoidCallback? onViewAll) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
        if (onViewAll != null)
          GestureDetector(
            onTap: onViewAll,
            child: const Text('View All', style: TextStyle(fontSize: 13, color: AppColors.primary, fontWeight: FontWeight.w500)),
          ),
      ],
    );
  }
}
