import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class RdcUpdateService {
  final AuthStorage _authStorage = AuthStorage();

  Future<UpdateRdcResult> updateRdc({
    required int rdcId,
    required Map<String, dynamic> payload,
  }) async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return UpdateRdcResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse('${ApiConstants.baseUrl}/api/mobile/rdcs/$rdcId/');

    try {
      final response = await http.patch(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode(payload),
      );

      final dynamic data =
          response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if ((response.statusCode == 200 || response.statusCode == 202) &&
          data is Map<String, dynamic>) {
        return UpdateRdcResult(
          success: true,
          data: data,
          message: 'RDC atualizado com sucesso.',
        );
      }

      return UpdateRdcResult(
        success: false,
        message: _extractMessage(data),
      );
    } catch (e) {
      return UpdateRdcResult(
        success: false,
        message: 'Erro de conexão ao atualizar o RDC.',
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
    return 'Não foi possível atualizar o RDC.';
  }
}

class UpdateRdcResult {
  final bool success;
  final Map<String, dynamic>? data;
  final String message;

  UpdateRdcResult({
    required this.success,
    this.data,
    required this.message,
  });
}
