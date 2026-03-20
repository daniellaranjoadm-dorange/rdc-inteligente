import 'package:flutter/material.dart';

import '../../../home/data/services/base_operacional_service.dart';
import '../../data/services/rdc_service.dart';

class NovoRdcPage extends StatefulWidget {
  const NovoRdcPage({super.key});

  @override
  State<NovoRdcPage> createState() => _NovoRdcPageState();
}

class _NovoRdcPageState extends State<NovoRdcPage> {
  final _formKey = GlobalKey<FormState>();
  final _rdcService = RdcService();

  String? _projetoId;
  String? _disciplinaId;
  String? _areaId;
  String _turno = 'manha';
  bool _isLoading = false;

  String _itemLabel(Map<String, dynamic> item) {
    final codigo = (item['codigo'] ?? '').toString().trim();
    final nome = (item['nome'] ?? item['descricao'] ?? '').toString().trim();

    if (codigo.isNotEmpty && nome.isNotEmpty) {
      return '$codigo - $nome';
    }
    if (nome.isNotEmpty) return nome;
    if (codigo.isNotEmpty) return codigo;
    return item.toString();
  }

  Future<void> _continuar() async {
    final isValid = _formKey.currentState?.validate() ?? false;
    if (!isValid) return;

    setState(() {
      _isLoading = true;
    });

    final result = await _rdcService.createRdc(
      projetoId: _projetoId!,
      disciplinaId: _disciplinaId!,
      areaLocalId: _areaId!,
      turno: _turno,
    );

    if (!mounted) return;

    setState(() {
      _isLoading = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(result.message)),
    );

    if (result.success) {
      final rdcId = result.data?['id'];
      if (rdcId is int) {
        Navigator.pushReplacementNamed(
          context,
          '/rdc-detalhe',
          arguments: {'rdcId': rdcId},
        );
      } else {
        Navigator.pop(context);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final service = BaseOperacionalService();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Novo RDC'),
      ),
      body: SafeArea(
        child: FutureBuilder<BaseOperacionalResult>(
          future: service.getBaseOperacional(),
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }

            final result = snapshot.data;
            final model = result?.model;

            if (result == null || !result.success || model == null) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    result?.message ?? 'Não foi possível carregar os dados.',
                    style: const TextStyle(color: Colors.redAccent),
                  ),
                ),
              );
            }

            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const Text(
                              'Preparação do RDC',
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Selecione os dados iniciais para abrir um novo RDC.',
                              style: TextStyle(
                                fontSize: 15,
                                color: Colors.grey,
                              ),
                            ),
                            const SizedBox(height: 24),
                            DropdownButtonFormField<String>(
                              value: _projetoId,
                              decoration: const InputDecoration(
                                labelText: 'Projeto',
                              ),
                              items: model.projetos.map((item) {
                                final id = item['id'].toString();
                                return DropdownMenuItem<String>(
                                  value: id,
                                  child: Text(_itemLabel(item)),
                                );
                              }).toList(),
                              onChanged: _isLoading
                                  ? null
                                  : (value) {
                                      setState(() {
                                        _projetoId = value;
                                      });
                                    },
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Selecione o projeto';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),
                            DropdownButtonFormField<String>(
                              value: _disciplinaId,
                              decoration: const InputDecoration(
                                labelText: 'Disciplina',
                              ),
                              items: model.disciplinas.map((item) {
                                final id = item['id'].toString();
                                return DropdownMenuItem<String>(
                                  value: id,
                                  child: Text(_itemLabel(item)),
                                );
                              }).toList(),
                              onChanged: _isLoading
                                  ? null
                                  : (value) {
                                      setState(() {
                                        _disciplinaId = value;
                                      });
                                    },
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Selecione a disciplina';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),
                            DropdownButtonFormField<String>(
                              value: _areaId,
                              decoration: const InputDecoration(
                                labelText: 'Área local',
                              ),
                              items: model.areas.map((item) {
                                final id = item['id'].toString();
                                return DropdownMenuItem<String>(
                                  value: id,
                                  child: Text(_itemLabel(item)),
                                );
                              }).toList(),
                              onChanged: _isLoading
                                  ? null
                                  : (value) {
                                      setState(() {
                                        _areaId = value;
                                      });
                                    },
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Selecione a área local';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),
                            DropdownButtonFormField<String>(
                              value: _turno,
                              decoration: const InputDecoration(
                                labelText: 'Turno',
                              ),
                              items: const [
                                DropdownMenuItem<String>(
                                  value: 'manha',
                                  child: Text('Manhã'),
                                ),
                                DropdownMenuItem<String>(
                                  value: 'tarde',
                                  child: Text('Tarde'),
                                ),
                                DropdownMenuItem<String>(
                                  value: 'noite',
                                  child: Text('Noite'),
                                ),
                              ],
                              onChanged: _isLoading
                                  ? null
                                  : (value) {
                                      if (value != null) {
                                        setState(() {
                                          _turno = value;
                                        });
                                      }
                                    },
                            ),
                            const SizedBox(height: 24),
                            ElevatedButton(
                              onPressed: _isLoading ? null : _continuar,
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 22,
                                      width: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.4,
                                      ),
                                    )
                                  : const Text('Continuar'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
