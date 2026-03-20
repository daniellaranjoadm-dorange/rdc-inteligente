import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class RdcService {
  final AuthStorage _authStorage = AuthStorage();

  Future<CreateRdcResult> createRdc({
    required String projetoId,
    required String disciplinaId,
    required String areaLocalId,
    required String turno,
  }) async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return CreateRdcResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse('${ApiConstants.baseUrl}/api/mobile/rdcs/');
    final today = DateTime.now();
    final dataHoje =
        '${today.year.toString().padLeft(4, '0')}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';

    final payload = {
      'projeto': int.parse(projetoId),
      'disciplina': int.parse(disciplinaId),
      'area_local': int.parse(areaLocalId),
      'data': dataHoje,
      'turno': turno,
      'observacoes': '',
    };

    try {
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode(payload),
      );

      final dynamic data =
          response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if ((response.statusCode == 200 || response.statusCode == 201) &&
          data is Map<String, dynamic>) {
        return CreateRdcResult(
          success: true,
          data: data,
          message: 'RDC criado com sucesso.',
        );
      }

      return CreateRdcResult(
        success: false,
        message: _extractMessage(data),
      );
    } catch (e) {
      return CreateRdcResult(
        success: false,
        message: 'Erro de conexão ao criar RDC.',
      );
    }
  }

  String _extractMessage(dynamic data) {
    if (data is Map<String, dynamic>) {
      if (data['detail'] != null) return data['detail'].toString();

      for (final entry in data.entries) {
        final value = entry.value;
        if (value is List && value.isNotEmpty) {
          return '${entry.key}: ${value.first}';
        }
        if (value is String && value.isNotEmpty) {
          return '${entry.key}: $value';
        }
      }
    }
    return 'Não foi possível criar o RDC.';
  }
}

class CreateRdcResult {
  final bool success;
  final Map<String, dynamic>? data;
  final String message;

  CreateRdcResult({
    required this.success,
    this.data,
    required this.message,
  });
}
