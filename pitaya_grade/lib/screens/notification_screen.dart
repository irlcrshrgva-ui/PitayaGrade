import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/notification_service.dart';

class NotificationScreen extends StatefulWidget {
  final NotificationService service;
  const NotificationScreen({super.key, required this.service});

  @override
  State<NotificationScreen> createState() => _NotificationScreenState();
}

class _NotificationScreenState extends State<NotificationScreen> {
  @override
  void initState() {
    super.initState();
    widget.service.markAllRead();
    widget.service.addListener(_update);
  }

  void _update() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    widget.service.removeListener(_update);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgSurface,
        elevation: 0,
        title: const Text('Notifications', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
        actions: [
          if (widget.service.notifications.isNotEmpty)
            TextButton(
              onPressed: () {
                widget.service.clearAll();
              },
              child: const Text('Clear All', style: TextStyle(fontSize: 13, color: AppColors.primary)),
            ),
        ],
      ),
      body: widget.service.notifications.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  Text('🔔', style: TextStyle(fontSize: 48)),
                  SizedBox(height: 12),
                  Text('No Notifications', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
                  SizedBox(height: 4),
                  Text('You\'re all caught up.', style: TextStyle(fontSize: 13, color: AppColors.textTertiary)),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: widget.service.notifications.length,
              itemBuilder: (_, i) {
                final n = widget.service.notifications[i];
                final color = widget.service.severityColor(n.severity);
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.bgCard,
                    borderRadius: BorderRadius.circular(12),
                    border: Border(left: BorderSide(color: color, width: 3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(n.icon, style: const TextStyle(fontSize: 22)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(n.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 2),
                            Text(n.body, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.4)),
                            const SizedBox(height: 4),
                            Text(widget.service.timeAgo(n.time), style: const TextStyle(fontSize: 11, color: AppColors.textTertiary)),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
