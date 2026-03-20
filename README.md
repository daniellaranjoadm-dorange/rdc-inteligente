# RDC Inteligente

Base inicial de um sistema Django modular para RDC inteligente, com foco em operação web, API REST e preparação para futuras integrações com app mobile e GED.

## Apps
- core
- accounts
- cadastros
- planejamento
- alocacao
- acesso
- rdc
- importacoes
- relatorios

## Fluxo principal
1. Usuário escolhe projeto, área/local, disciplina, data e turno.
2. Serviço `montar_rdc_pre_preenchido` cruza cronograma, histograma, alocação e catraca.
3. Sistema cria o cabeçalho do RDC, atividades, funcionários elegíveis/bloqueados e validações.
4. Estrutura fica pronta para detalhamento web, API e futura geração de PDF.

## Observações
- O endpoint `POST /api/rdc/montar/` está preparado para automação do pré-preenchimento.
- O app `importacoes` traz base genérica para importação de CSV/XLSX.
- O app `relatorios` traz serviço inicial para estrutura de dados voltada ao PDF do RDC.
