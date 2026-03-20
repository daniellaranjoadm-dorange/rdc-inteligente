import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/data/services/auth_service.dart';
import 'features/auth/presentation/pages/login_page.dart';
import 'features/home/presentation/pages/home_page.dart';
import 'features/rdc/presentation/pages/novo_rdc_page.dart';
import 'features/rdc/presentation/pages/rdc_detail_page.dart';
import 'features/rdc/presentation/pages/rdc_list_page.dart';

class RdcMobileApp extends StatelessWidget {
  const RdcMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RDC Mobile',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const AppStartPage(),
      routes: {
        '/login': (_) => const LoginPage(),
        '/home': (_) => const HomePage(),
        '/novo-rdc': (_) => const NovoRdcPage(),
        '/rdc-list': (_) => const RdcListPage(),
      },
      onGenerateRoute: (settings) {
        if (settings.name == '/rdc-detalhe') {
          final args = settings.arguments as Map<String, dynamic>?;
          final rdcId = args?['rdcId'] as int?;

          if (rdcId != null) {
            return MaterialPageRoute(
              builder: (_) => RdcDetailPage(rdcId: rdcId),
            );
          }
        }
        return null;
      },
    );
  }
}

class AppStartPage extends StatelessWidget {
  const AppStartPage({super.key});

  @override
  Widget build(BuildContext context) {
    final authService = AuthService();

    return FutureBuilder<bool>(
      future: authService.isLoggedIn(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        final isLoggedIn = snapshot.data ?? false;
        return isLoggedIn ? const HomePage() : const LoginPage();
      },
    );
  }
}
