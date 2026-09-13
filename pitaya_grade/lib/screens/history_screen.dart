import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/database_service.dart';
import '../models/scan_result.dart';
import '../widgets/grade_badge.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<ScanResult> _scans = [];
  String _activeFilter = 'all';
  String _searchQuery = '';
  bool _loading = true;

  final _filters = ['All', 'Grade A', 'Grade B', 'Grade C', 'Reject', 'Diseased'];

  @override
  void initState() {
    super.initState();
    _loadScans();
  }

  Future<void> _loadScans() async {
    List<ScanResult> scans;
    switch (_activeFilter) {
      case 'Grade A':
      case 'Grade B':
      case 'Grade C':
        scans = await DatabaseService.getScansByGrade(_activeFilter);
        break;
      case 'Reject':
        scans = await DatabaseService.getScansByGrade('Reject');
        break;
      case 'Diseased':
        scans = await DatabaseService.getDiseasedScans();
        break;
      default:
        scans = await DatabaseService.getAllScans();
    }

    // Search filter
    if (_searchQuery.isNotEmpty) {
      scans = scans.where((s) {
        final searchable = '${s.grade.label} ${s.disease.name} ${s.notes} ${s.details.surfaceCondition}'.toLowerCase();
        return searchable.contains(_searchQuery.toLowerCase());
      }).toList();
    }

    if (mounted) setState(() { _scans = scans; _loading = false; });
  }

  Future<void> _deleteScan(String id) async {
    await DatabaseService.deleteScan(id);
    _loadScans();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Record deleted'),
          backgroundColor: AppColors.bgElevated,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    }
  }

  void _showDetail(ScanResult scan) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.bgSurface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (_, scrollCtrl) => _buildDetailSheet(scan, scrollCtrl),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Scan History', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              const Text('All your recorded assessments', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
              const SizedBox(height: 16),
              // Search
              TextField(
                onChanged: (v) { _searchQuery = v; _loadScans(); },
                decoration: InputDecoration(
                  hintText: 'Search by notes, grade, disease...',
                  prefixIcon: const Padding(
                    padding: EdgeInsets.only(left: 12, right: 8),
                    child: Text('🔍', style: TextStyle(fontSize: 16)),
                  ),
                  prefixIconConstraints: const BoxConstraints(minWidth: 40),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),

        // Filter chips
        SizedBox(
          height: 36,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: _filters.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (_, i) {
              final f = _filters[i];
              final isActive = _activeFilter == (f == 'All' ? 'all' : f);
              return GestureDetector(
                onTap: () {
                  setState(() => _activeFilter = f == 'All' ? 'all' : f);
                  _loadScans();
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: isActive ? AppColors.primary : AppColors.bgCard,
                    border: Border.all(
                      color: isActive ? AppColors.primary : Colors.white.withOpacity(0.06),
                    ),
                  ),
                  child: Center(
                    child: Text(
                      f,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: isActive ? Colors.white : AppColors.textSecondary,
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 12),

        // List
        Expanded(
          child: _scans.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Text('📋', style: TextStyle(fontSize: 48)),
                      SizedBox(height: 12),
                      Text('No records found', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
                      SizedBox(height: 4),
                      Text('Try adjusting your filters.', style: TextStyle(fontSize: 13, color: AppColors.textTertiary)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  color: AppColors.primary,
                  backgroundColor: AppColors.bgCard,
                  onRefresh: _loadScans,
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _scans.length,
                    itemBuilder: (_, i) => _buildScanItem(_scans[i]),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildScanItem(ScanResult scan) {
    final time = '${scan.timestamp.day}/${scan.timestamp.month} ${scan.timestamp.hour.toString().padLeft(2, '0')}:${scan.timestamp.minute.toString().padLeft(2, '0')}';
    return Dismissible(
      key: Key(scan.id),
      direction: DismissDirection.endToStart,
      background: Container(
        margin: const EdgeInsets.only(bottom: 8),
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          color: AppColors.error.withOpacity(0.2),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Text('🗑️', style: TextStyle(fontSize: 24)),
      ),
      onDismissed: (_) => _deleteScan(scan.id),
      child: GestureDetector(
        onTap: () => _showDetail(scan),
        child: Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.06)),
          ),
          child: Row(
            children: [
              Container(
                width: 50, height: 50,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  color: AppColors.bgElevated,
                ),
                child: scan.thumbnail != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.memory(scan.thumbnail!, fit: BoxFit.cover),
                      )
                    : const Center(child: Text('🐉', style: TextStyle(fontSize: 22))),
              ),
              const SizedBox(width: 12),
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
                    Text('$time | ${scan.details.size}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                  ],
                ),
              ),
              GradeBadge(grade: scan.grade.label),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailSheet(ScanResult scan, ScrollController scrollCtrl) {
    final gradeColor = AppColors.gradeColor(scan.grade.label);
    return ListView(
      controller: scrollCtrl,
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: Container(width: 36, height: 4, decoration: BoxDecoration(color: AppColors.textTertiary, borderRadius: BorderRadius.circular(2))),
        ),
        const SizedBox(height: 16),
        Center(
          child: Container(
            width: 100, height: 100,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: AppColors.bgElevated,
              border: Border.all(color: Colors.white.withOpacity(0.1), width: 2),
            ),
            child: scan.thumbnail != null
                ? ClipRRect(borderRadius: BorderRadius.circular(14), child: Image.memory(scan.thumbnail!, fit: BoxFit.cover))
                : const Center(child: Text('🐉', style: TextStyle(fontSize: 40))),
          ),
        ),
        const SizedBox(height: 16),
        Center(child: GradeBadge(grade: scan.grade.label, large: true)),
        const SizedBox(height: 8),
        Center(child: Text('${(scan.grade.confidence * 100).toStringAsFixed(1)}% confidence', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary))),
        const SizedBox(height: 8),
        Center(
          child: Text(
            '${scan.timestamp.day}/${scan.timestamp.month}/${scan.timestamp.year} ${scan.timestamp.hour.toString().padLeft(2, '0')}:${scan.timestamp.minute.toString().padLeft(2, '0')}',
            style: const TextStyle(fontSize: 11, color: AppColors.textTertiary),
          ),
        ),
        const SizedBox(height: 20),

        // Disease
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: (scan.disease.isHealthy ? AppColors.success : AppColors.error).withOpacity(0.1),
            border: Border.all(color: (scan.disease.isHealthy ? AppColors.success : AppColors.error).withOpacity(0.2)),
          ),
          child: Row(
            children: [
              Text(scan.disease.isHealthy ? '✅' : '⚠️', style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 10),
              Expanded(child: Text(scan.disease.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
              Text('${(scan.disease.confidence * 100).toStringAsFixed(1)}%', style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // Details
        _detailRow('📏 Size', scan.details.size),
        _detailRow('🎨 Color Uniformity', scan.details.colorUniformity),
        _detailRow('🔬 Surface', scan.details.surfaceCondition),
        _detailRow('📶 Mode', scan.details.processingMode),
        _detailRow('⚡ Time', scan.details.processingTime),
        const SizedBox(height: 20),

        // Recommendations
        ...scan.recommendations.map((r) {
          final color = r.type == RecommendationType.positive ? AppColors.success : r.type == RecommendationType.warning ? AppColors.warning : AppColors.error;
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
                Text(r.icon, style: const TextStyle(fontSize: 18)),
                const SizedBox(width: 10),
                Expanded(child: Text(r.text, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.5))),
              ],
            ),
          );
        }),

        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () { Navigator.pop(context); _deleteScan(scan.id); },
            icon: const Text('🗑️'),
            label: const Text('Delete Record'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.error,
              side: const BorderSide(color: AppColors.error),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
      ],
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
}
