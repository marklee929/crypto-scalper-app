import 'dart:io';
import 'package:flutter/material.dart';

Color _getColorForLine(String line) {
  if (line.contains('[WARNING]')) return Colors.yellow[700]!;
  if (line.contains('[ERROR]')) return Colors.red;
  if (line.contains('[DEBUG]')) return Colors.green;
  return Colors.blue;
}
