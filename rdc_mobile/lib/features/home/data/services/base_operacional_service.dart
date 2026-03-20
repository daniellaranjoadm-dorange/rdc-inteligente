import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';
import '../models/base_operacional_model.dart';

class BaseOperacionalService {
  final AuthStorage _authStorage = AuthStorage();

  Future<BaseOperacionalResult> getBaseOperacional() async {
    final token = await _authStorage.getAccessToken();

    if (token == null || token.isEmpty) {
      return BaseOperacionalResult(
        success: false,
        message: 'Token não encontrado.',
      );
    }

    final uri = Uri.parse('${ApiConstants.baseUrl}/api/mobile/base-operacional/');

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
        return BaseOperacionalResult(
          success: true,
          rawData: data,
          model: BaseOperacionalModel.fromMap(data),
          message: 'Base operacional carregada com sucesso.',
        );
      }

      return BaseOperacionalResult(
        success: false,
        message: 'Não foi possível carregar a base operacional.',
      );
    } catch (e) {
      return BaseOperacionalResult(
        success: false,
        message: 'Erro de conexão ao buscar base operacional.',
      );
    }
  }
}

class BaseOperacionalResult {
  final bool success;
  final Map<String, dynamic>? rawData;
  final BaseOperacionalModel? model;
  final String message;

  BaseOperacionalResult({
    required this.success,
    this.rawData,
    this.model,
    required this.message,
  });
}
