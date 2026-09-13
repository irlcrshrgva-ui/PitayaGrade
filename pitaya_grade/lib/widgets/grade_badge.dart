import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class GradeBadge extends StatelessWidget {
  final String grade;
  final bool large;

  const GradeBadge({super.key, required this.grade, this.large = false});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.gradeColor(grade);
    final shortLabel = _shortLabel(grade);
    final size = large ? 56.0 : 36.0;
    final fontSize = large ? 20.0 : 13.0;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(large ? 16 : 10),
        color: color.withOpacity(0.15),
        border: Border.all(color: color.withOpacity(0.3), width: large ? 2 : 1.5),
      ),
      child: Center(
        child: Text(
          shortLabel,
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ),
    );
  }

  String _shortLabel(String grade) {
    switch (grade) {
      case 'Grade A':
        return 'A';
      case 'Grade B':
        return 'B';
      case 'Grade C':
        return 'C';
      case 'Reject':
        return 'R';
      default:
        return '?';
    }
  }
}
