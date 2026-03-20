class BaseOperacionalModel {
  final List<Map<String, dynamic>> projetos;
  final List<Map<String, dynamic>> disciplinas;
  final List<Map<String, dynamic>> areas;
  final List<Map<String, dynamic>> equipes;
  final List<Map<String, dynamic>> funcionarios;
  final List<Map<String, dynamic>> rdcs;

  BaseOperacionalModel({
    required this.projetos,
    required this.disciplinas,
    required this.areas,
    required this.equipes,
    required this.funcionarios,
    required this.rdcs,
  });

  factory BaseOperacionalModel.fromMap(Map<String, dynamic> map) {
    List<Map<String, dynamic>> asMapList(dynamic value) {
      if (value is List) {
        return value
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
      }
      return [];
    }

    return BaseOperacionalModel(
      projetos: asMapList(map['projetos']),
      disciplinas: asMapList(map['disciplinas']),
      areas: asMapList(map['areas']),
      equipes: asMapList(map['equipes']),
      funcionarios: asMapList(map['funcionarios']),
      rdcs: asMapList(map['rdcs']),
    );
  }
}
