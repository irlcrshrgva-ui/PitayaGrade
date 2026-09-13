import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/database_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notifications = true;
  bool _offlineMode = false;
  String _language = 'English';

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Settings', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        const Text('Configure your preferences', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
        const SizedBox(height: 24),

        // General
        _groupTitle('General'),
        _settingsCard([
          _settingsTile(
            icon: '🌐', label: 'Language', subtitle: _language,
            trailing: _actionButton('Switch', () {
              setState(() => _language = _language == 'English' ? 'Filipino' : 'English');
            }),
          ),
          _divider(),
          _settingsTile(
            icon: '🔔', label: 'Push Notifications', subtitle: 'Get alerts for disease detections',
            trailing: _toggle(_notifications, (v) => setState(() => _notifications = v)),
          ),
          _divider(),
          _settingsTile(
            icon: '📶', label: 'Offline Mode', subtitle: 'Use on-device TFLite model',
            trailing: _toggle(_offlineMode, (v) => setState(() => _offlineMode = v)),
          ),
        ]),
        const SizedBox(height: 24),

        // ML Model
        _groupTitle('ML Model'),
        _settingsCard([
          _settingsTile(
            icon: '🧠', label: 'Model Version', subtitle: 'YOLOv8-Nano v8.1.0',
            trailing: const Text('Up to date', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.success)),
          ),
          _divider(),
          _settingsTile(
            icon: '🎯', label: 'Detection Threshold', subtitle: '65%',
            trailing: const Icon(Icons.chevron_right, color: AppColors.textTertiary, size: 20),
          ),
        ]),
        const SizedBox(height: 24),

        // Data
        _groupTitle('Data'),
        _settingsCard([
          _settingsTile(
            icon: '🗑️', label: 'Clear All Data', subtitle: 'Remove all scan records',
            labelColor: AppColors.error,
            onTap: _clearData,
            trailing: const Icon(Icons.chevron_right, color: AppColors.textTertiary, size: 20),
          ),
        ]),
        const SizedBox(height: 32),

        // App info
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.06)),
          ),
          child: Column(
            children: const [
              Text('🐉', style: TextStyle(fontSize: 36)),
              SizedBox(height: 8),
              Text('PitayaGrade v1.0.0', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              SizedBox(height: 4),
              Text('Pre-Harvest Quality Grading\n& Disease Detection', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: AppColors.textTertiary)),
              SizedBox(height: 8),
              Text('Capstone Project 2025-2026', style: TextStyle(fontSize: 11, color: AppColors.textTertiary)),
            ],
          ),
        ),
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _groupTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 8, bottom: 8),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 1, color: AppColors.textTertiary),
      ),
    );
  }

  Widget _settingsCard(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(children: children),
    );
  }

  Widget _settingsTile({
    required String icon,
    required String label,
    String? subtitle,
    Widget? trailing,
    Color? labelColor,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                color: AppColors.bgElevated,
              ),
              child: Center(child: Text(icon, style: const TextStyle(fontSize: 18))),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: labelColor ?? AppColors.textPrimary)),
                  if (subtitle != null)
                    Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                ],
              ),
            ),
            if (trailing != null) trailing!,
          ],
        ),
      ),
    );
  }

  Widget _toggle(bool value, ValueChanged<bool> onChanged) {
    return GestureDetector(
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        width: 44, height: 24,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: value ? AppColors.primary : AppColors.bgElevated,
          border: Border.all(color: value ? AppColors.primary : Colors.white.withOpacity(0.1)),
        ),
        child: AnimatedAlign(
          duration: const Duration(milliseconds: 250),
          alignment: value ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            width: 18, height: 18,
            margin: const EdgeInsets.symmetric(horizontal: 2),
            decoration: const BoxDecoration(shape: BoxShape.circle, color: Colors.white),
          ),
        ),
      ),
    );
  }

  Widget _actionButton(String text, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          color: AppColors.bgElevated,
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
      ),
    );
  }

  Widget _divider() {
    return Divider(height: 1, indent: 66, color: Colors.white.withOpacity(0.06));
  }

  Future<void> _clearData() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.bgSurface,
        title: const Text('Clear All Data?'),
        content: const Text('This will permanently delete all scan records. This action cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await DatabaseService.deleteAllScans();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('All data cleared'),
            backgroundColor: AppColors.bgElevated,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    }
  }
}
