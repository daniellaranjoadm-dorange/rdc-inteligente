import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/constants/api_constants.dart';
import '../../../../core/storage/auth_storage.dart';

class AuthService {
  final AuthStorage _authStorage = AuthStorage();

  Future<AuthResult> login({
    required String username,
    required String password,
  }) async {
    final uri = Uri.parse(ApiConstants.tokenUrl);

    try {
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      final dynamic data =
          response.body.isNotEmpty ? jsonDecode(response.body) : {};

      if (response.statusCode == 200) {
        final accessToken = data['access']?.toString();
        final refreshToken = data['refresh']?.toString();

        if (accessToken != null &&
            accessToken.isNotEmpty &&
            refreshToken != null &&
            refreshToken.isNotEmpty) {
          await _authStorage.saveTokens(
            accessToken: accessToken,
            refreshToken: refreshToken,
          );
        }

        return AuthResult(
          success: true,
          accessToken: accessToken,
          refreshToken: refreshToken,
          message: 'Login realizado com sucesso.',
        );
      }

      return AuthResult(
        success: false,
        message: _extractErrorMessage(data),
      );
    } catch (e) {
      return AuthResult(
        success: false,
        message: 'Não foi possível conectar à API. Verifique se o servidor Django está rodando.',
      );
    }
  }

  Future<void> logout() async {
    await _authStorage.clear();
  }

  Future<bool> isLoggedIn() async {
    return _authStorage.isLoggedIn();
  }

  String _extractErrorMessage(dynamic data) {
    if (data is Map<String, dynamic>) {
      if (data['detail'] != null) {
        return data['detail'].toString();
      }

      if (data['message'] != null) {
        return data['message'].toString();
      }

      if (data['non_field_errors'] is List && data['non_field_errors'].isNotEmpty) {
        return data['non_field_errors'].first.toString();
      }

      if (data['username'] is List && data['username'].isNotEmpty) {
        return data['username'].first.toString();
      }

      if (data['password'] is List && data['password'].isNotEmpty) {
        return data['password'].first.toString();
      }
    }

    return 'Usuário ou senha inválidos.';
  }
}

class AuthResult {
  final bool success;
  final String? accessToken;
  final String? refreshToken;
  final String message;

  AuthResult({
    required this.success,
    this.accessToken,
    this.refreshToken,
    required this.message,
  });
}
