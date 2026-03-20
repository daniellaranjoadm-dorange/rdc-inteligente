import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class MeService {
  final AuthStorage _authStorage = AuthStorage();

  Future<MeResult> getMe() async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return MeResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse(ApiConstants.meUrl);

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
        return MeResult(
          success: true,
          data: data,
          message: 'Dados carregados com sucesso.',
        );
      }

      return MeResult(
        success: false,
        message: 'Não foi possível carregar os dados do usuário.',
      );
    } catch (e) {
      return MeResult(
        success: false,
        message: 'Erro de conexão ao buscar usuário logado.',
      );
    }
  }
}

class MeResult {
  final bool success;
  final Map<String, dynamic>? data;
  final String message;

  MeResult({
    required this.success,
    this.data,
    required this.message,
  });
}
