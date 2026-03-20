import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class RdcListService {
  final AuthStorage _authStorage = AuthStorage();

  Future<RdcListResult> getRdcs() async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return RdcListResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse('${ApiConstants.baseUrl}/api/mobile/rdcs/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      final dynamic data =
          response.body.isNotEmpty ? jsonDecode(response.body) : [];

      if (response.statusCode == 200 && data is List) {
        return RdcListResult(
          success: true,
          items: data.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
          message: 'RDCs carregados com sucesso.',
        );
      }

      return RdcListResult(
        success: false,
        message: 'Não foi possível carregar os RDCs.',
      );
    } catch (e) {
      return RdcListResult(
        success: false,
        message: 'Erro de conexão ao buscar os RDCs.',
      );
    }
  }
}

class RdcListResult {
  final bool success;
  final List<Map<String, dynamic>> items;
  final String message;

  RdcListResult({
    required this.success,
    this.items = const [],
    required this.message,
  });
}
