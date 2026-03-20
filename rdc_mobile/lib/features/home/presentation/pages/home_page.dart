import 'package:flutter/material.dart';

import '../../../auth/data/services/auth_service.dart';
import '../../../auth/data/services/me_service.dart';
import '../../data/services/base_operacional_service.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  Future<void> _logout(BuildContext context) async {
    final authService = AuthService();
    await authService.logout();

    if (!context.mounted) return;
    Navigator.pushReplacementNamed(context, '/login');
  }

  @override
  Widget build(BuildContext context) {
    final meService = MeService();
    final baseService = BaseOperacionalService();

    return Scaffold(
      appBar: AppBar(
        title: const Text('RDC Mobile'),
        actions: [
          IconButton(
            tooltip: 'Sair',
            onPressed: () => _logout(context),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SafeArea(
        child: FutureBuilder<List<dynamic>>(
          future: Future.wait([
            meService.getMe(),
            baseService.getBaseOperacional(),
          ]),
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }

            final meResult = snapshot.data?[0] as MeResult?;
            final baseResult = snapshot.data?[1] as BaseOperacionalResult?;

            final user = meResult?.data ?? {};
            final model = baseResult?.model;

            final firstName = (user['first_name'] ?? '').toString().trim();
            final lastName = (user['last_name'] ?? '').toString().trim();
            final username = (user['username'] ?? '').toString().trim();
            final email = (user['email'] ?? '').toString().trim();

            final displayName = [firstName, lastName]
                .where((e) => e.isNotEmpty)
                .join(' ')
                .trim();

            final projetos = model?.projetos.length ?? 0;
            final equipes = model?.equipes.length ?? 0;
            final funcionarios = model?.funcionarios.length ?? 0;
            final rdcs = model?.rdcs.length ?? 0;

            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        displayName.isNotEmpty ? 'Olá, $displayName!' : 'Olá!',
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        username.isNotEmpty
                            ? 'Usuário: $username'
                            : 'Bem-vindo ao ambiente inicial do RDC Mobile.',
                        style: const TextStyle(
                          fontSize: 16,
                          color: Colors.grey,
                        ),
                      ),
                      if (email.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          email,
                          style: const TextStyle(
                            fontSize: 14,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                      if (baseResult != null && !baseResult.success) ...[
                        const SizedBox(height: 12),
                        Text(
                          baseResult.message,
                          style: const TextStyle(
                            fontSize: 14,
                            color: Colors.redAccent,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      Wrap(
                        spacing: 16,
                        runSpacing: 16,
                        children: [
                          _SummaryCard(title: 'Projetos', value: projetos.toString()),
                          _SummaryCard(title: 'Equipes', value: equipes.toString()),
                          _SummaryCard(title: 'Funcionários', value: funcionarios.toString()),
                          _SummaryCard(title: 'RDCs do dia', value: rdcs.toString()),
                        ],
                      ),
                      const SizedBox(height: 24),
                      Wrap(
                        spacing: 16,
                        runSpacing: 16,
                        children: [
                          _ActionCard(
                            title: 'Novo RDC',
                            subtitle: 'Iniciar um novo relatório diário de campo.',
                            icon: Icons.note_add_outlined,
                            onTap: () => Navigator.pushNamed(context, '/novo-rdc'),
                          ),
                          _ActionCard(
                            title: 'Rascunhos',
                            subtitle: 'Consultar RDCs já criados.',
                            icon: Icons.edit_note_outlined,
                            onTap: () => Navigator.pushNamed(context, '/rdc-list'),
                          ),
                          const _ActionCard(
                            title: 'Sincronização',
                            subtitle: 'Enviar e atualizar dados com o servidor.',
                            icon: Icons.sync_outlined,
                          ),
                        ],
                      ),
                    ],
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

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;

  const _SummaryCard({
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 250,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 15,
                  color: Colors.grey,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback? onTap;

  const _ActionCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 340,
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  icon,
                  size: 36,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 16),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 14,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
