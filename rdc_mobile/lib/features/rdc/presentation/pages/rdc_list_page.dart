import 'package:flutter/material.dart';

import '../../data/services/rdc_list_service.dart';

class RdcListPage extends StatelessWidget {
  const RdcListPage({super.key});

  String _text(dynamic value, {String fallback = '-'}) {
    if (value == null) return fallback;
    final s = value.toString().trim();
    return s.isEmpty ? fallback : s;
  }

  Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return {};
  }

  int? _asInt(dynamic value) {
    if (value is int) return value;
    if (value is String) return int.tryParse(value);
    return null;
  }

  String _projetoText(dynamic value) {
    final map = _asMap(value);
    if (map.isNotEmpty) {
      final codigo = _text(map['codigo'], fallback: '');
      final nome = _text(map['nome'], fallback: '');
      if (codigo.isNotEmpty && nome.isNotEmpty) return '$codigo - $nome';
      if (nome.isNotEmpty) return nome;
      if (codigo.isNotEmpty) return codigo;
    }
    return _text(value);
  }

  String _areaText(dynamic value) {
    final map = _asMap(value);
    if (map.isNotEmpty) {
      final codigo = _text(map['codigo'], fallback: '');
      final descricao = _text(map['descricao'], fallback: '');
      if (codigo.isNotEmpty && descricao.isNotEmpty) {
        return '$codigo - $descricao';
      }
      if (descricao.isNotEmpty) return descricao;
      if (codigo.isNotEmpty) return codigo;
    }
    return _text(value);
  }

  String _disciplinaText(dynamic value) {
    final map = _asMap(value);
    if (map.isNotEmpty) {
      final nome = _text(map['nome'], fallback: '');
      final codigo = _text(map['codigo'], fallback: '');
      if (nome.isNotEmpty) return nome;
      if (codigo.isNotEmpty) return codigo;
    }
    return _text(value);
  }

  @override
  Widget build(BuildContext context) {
    final service = RdcListService();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Rascunhos / RDCs'),
      ),
      body: SafeArea(
        child: FutureBuilder<RdcListResult>(
          future: service.getRdcs(),
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }

            final result = snapshot.data;

            if (result == null || !result.success) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    result?.message ?? 'Não foi possível carregar os RDCs.',
                    style: const TextStyle(
                      color: Colors.redAccent,
                      fontSize: 16,
                    ),
                  ),
                ),
              );
            }

            final items = result.items;

            if (items.isEmpty) {
              return const Center(
                child: Text(
                  'Nenhum RDC encontrado.',
                  style: TextStyle(fontSize: 16),
                ),
              );
            }

            return ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final item = items[index];
                final id = _asInt(item['id']);

                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'RDC #${_text(item['id'])}',
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text('Projeto: ${_projetoText(item['projeto'])}'),
                        const SizedBox(height: 4),
                        Text('Área: ${_areaText(item['area_local'])}'),
                        const SizedBox(height: 4),
                        Text('Disciplina: ${_disciplinaText(item['disciplina'])}'),
                        const SizedBox(height: 4),
                        Text('Data: ${_text(item['data'])}'),
                        const SizedBox(height: 4),
                        Text('Turno: ${_text(item['turno'])}'),
                        const SizedBox(height: 4),
                        Text('Status: ${_text(item['status'])}'),
                        const SizedBox(height: 14),
                        ElevatedButton(
                          onPressed: id == null
                              ? null
                              : () {
                                  Navigator.pushNamed(
                                    context,
                                    '/rdc-detalhe',
                                    arguments: {'rdcId': id},
                                  );
                                },
                          child: const Text('Abrir'),
                        ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
