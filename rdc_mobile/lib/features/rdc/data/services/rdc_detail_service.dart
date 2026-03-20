import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class RdcDetailService {
  final AuthStorage _authStorage = AuthStorage();

  Future<RdcDetailResult> getDetail(int rdcId) async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return RdcDetailResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse('${ApiConstants.baseUrl}/api/mobile/rdcs/$rdcId/detalhe/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      final dynamic data =
          response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if (response.statusCode == 200 && data is Map<String, dynamic>) {
        return RdcDetailResult(
          success: true,
          data: data,
          message: 'Detalhe do RDC carregado com sucesso.',
        );
      }

      return RdcDetailResult(
        success: false,
        message: _extractMessage(data),
      );
    } catch (e) {
      return RdcDetailResult(
        success: false,
        message: 'Erro de conexão ao carregar o detalhe do RDC.',
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
    return 'Não foi possível carregar o detalhe do RDC.';
  }
}

class RdcDetailResult {
  final bool success;
  final Map<String, dynamic>? data;
  final String message;

  RdcDetailResult({
    required this.success,
    this.data,
    required this.message,
  });
}
