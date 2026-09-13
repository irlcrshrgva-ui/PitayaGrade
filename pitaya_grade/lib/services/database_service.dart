import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/scan_result.dart';

class DatabaseService {
  static Database? _database;
  static const String _tableName = 'scans';

  static Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB();
    return _database!;
  }

  static Future<Database> _initDB() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'pitayagrade.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE $_tableName (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            imagePath TEXT,
            gradeLabel TEXT NOT NULL,
            gradeConfidence REAL NOT NULL,
            diseaseName TEXT NOT NULL,
            diseaseConfidence REAL NOT NULL,
            diseaseIsHealthy INTEGER NOT NULL,
            detailsSize TEXT,
            detailsColorUniformity TEXT,
            detailsSurfaceCondition TEXT,
            detailsProcessingMode TEXT,
            detailsProcessingTime TEXT,
            notes TEXT DEFAULT ''
          )
        ''');
      },
    );
  }

  static Future<void> insertScan(ScanResult scan) async {
    final db = await database;
    await db.insert(
      _tableName,
      scan.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<List<ScanResult>> getAllScans() async {
    final db = await database;
    final maps = await db.query(
      _tableName,
      orderBy: 'timestamp DESC',
    );
    return maps.map((map) => ScanResult.fromMap(map)).toList();
  }

  static Future<List<ScanResult>> getScansInRange(DateTime from, DateTime to) async {
    final db = await database;
    final maps = await db.query(
      _tableName,
      where: 'timestamp >= ? AND timestamp <= ?',
      whereArgs: [from.toIso8601String(), to.toIso8601String()],
      orderBy: 'timestamp DESC',
    );
    return maps.map((map) => ScanResult.fromMap(map)).toList();
  }

  static Future<List<ScanResult>> getScansByGrade(String grade) async {
    final db = await database;
    final maps = await db.query(
      _tableName,
      where: 'gradeLabel = ?',
      whereArgs: [grade],
      orderBy: 'timestamp DESC',
    );
    return maps.map((map) => ScanResult.fromMap(map)).toList();
  }

  static Future<List<ScanResult>> getDiseasedScans() async {
    final db = await database;
    final maps = await db.query(
      _tableName,
      where: 'diseaseIsHealthy = 0',
      orderBy: 'timestamp DESC',
    );
    return maps.map((map) => ScanResult.fromMap(map)).toList();
  }

  static Future<void> deleteScan(String id) async {
    final db = await database;
    await db.delete(_tableName, where: 'id = ?', whereArgs: [id]);
  }

  static Future<void> deleteAllScans() async {
    final db = await database;
    await db.delete(_tableName);
  }

  static Future<int> getScanCount() async {
    final db = await database;
    final result = await db.rawQuery('SELECT COUNT(*) as count FROM $_tableName');
    return result.first['count'] as int;
  }

  static Future<Map<String, int>> getGradeDistribution() async {
    final db = await database;
    final result = await db.rawQuery(
      'SELECT gradeLabel, COUNT(*) as count FROM $_tableName GROUP BY gradeLabel'
    );
    final map = <String, int>{};
    for (final row in result) {
      map[row['gradeLabel'] as String] = row['count'] as int;
    }
    return map;
  }

  static Future<Map<String, int>> getDiseaseDistribution() async {
    final db = await database;
    final result = await db.rawQuery(
      'SELECT diseaseName, COUNT(*) as count FROM $_tableName WHERE diseaseIsHealthy = 0 GROUP BY diseaseName'
    );
    final map = <String, int>{};
    for (final row in result) {
      map[row['diseaseName'] as String] = row['count'] as int;
    }
    return map;
  }
}
