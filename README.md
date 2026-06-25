Olá, eu sou o Daniel 👋

Desenvolvedor Back-end especializado em PHP/Laravel, com foco em arquitetura de sistemas web, deploy e infraestrutura Linux. 5 anos transformando processos manuais e sistemas legados em aplicações modernas e escaláveis.

📍 São Paulo, Brasil
💼 [LinkedIn](https://www.linkedin.com/in/dani-alves-dev/)
🌐 Inglês profissional

🚀 Projeto público

**[taskflow-api](https://github.com/danwson/taskflow-api)**

API REST em Laravel 11 para gestão de tarefas em times, com sistema de webhooks assíncronos orientado a eventos (Events → Listeners → Jobs via Redis Queue). Autenticação via Sanctum, 7 entidades com políticas de autorização, dashboard web com Kanban, 41 testes automatizados (Pest), containerizado com Docker e CI/CD via GitHub Actions.

`Laravel` `PHP` `MySQL` `Redis` `Sanctum` `Docker` `API REST` `Webhooks`

🏢 Case studies — sistemas em produção

Os projetos abaixo foram desenvolvidos por mim de forma autônoma — do planejamento à infraestrutura — para a FUNAP (Fundação Prof. Dr. Manoel Pedro Pimentel). O código é confidencial por se tratar de sistemas institucionais internos, mas os cases abaixo resumem a arquitetura, desafios e decisões técnicas.

📋 Sistema de Ouvidoria

Substituição de uma planilha de controle manual por um sistema web completo de gestão de manifestações.

O que foi construído:

- CRUD de manifestações com filtros, prazos com indicação visual e fluxo de finalização
- Dashboard analítico em tempo real — situação das manifestações, pendências por encaminhamento e resumo mensal
- Geração de relatórios em PDF com indicadores mensais (DomPDF)
- Módulo administrativo com 6 sub-CRUDs (encaminhamento, conclusão, tipo, contato, pesquisa, unidades)
- Autenticação com 3 perfis de acesso (Administrador, Ouvidoria, Consulta), cada um com permissões específicas

Stack: `Laravel 11` `MySQL` `DomPDF` `Blade`

Infraestrutura: servidor Debian 11 configurado do zero (Apache, PHP 8.4-FPM, MariaDB), publicado em ambiente interno da FUNAP.

🏠 Intranet FUNAP

Migração completa da intranet institucional de uma plataforma legada (Scriptcase 9) para uma arquitetura moderna, mantendo a mesma base de infraestrutura do projeto de Ouvidoria.

Módulos desenvolvidos (8 no total, cada um com área pública e painel administrativo):

| Módulo | Público | Admin |
|---|---|---|
| Notícias | Listagem, detalhe, PDF | CRUD completo |
| Aniversariantes | Lista por mês, destaque do dia | CRUD + import CSV |
| Destaques | Galeria com lightbox | CRUD com upload |
| Ramais | Agrupado por Diretoria/Setor | CRUD + import CSV |
| Sistemas | Grid por grupo com logo | CRUD completo |
| Mídia | Downloads por grupo | CRUD com upload |
| Redes Sociais | Widget na home | CRUD com logo |
| Usuários | — | Restrito ao administrador |

Stack: `Laravel 11` `Tailwind CSS` `MariaDB` `Blade`

Infraestrutura: mesmo servidor Debian 11, com banco populado via importação CSV (aniversariantes, diretorias, setores, ramais e sistemas).

🔧 Infraestrutura & DevOps

Além do desenvolvimento das aplicações, também sou responsável pela infraestrutura que sustenta esses sistemas:

- Backup automatizado: script de dump do MariaDB com compressão, retenção de 7 dias e limpeza automática, agendado via cron
- Monitoramento: alerta de uso de disco acima de 80%
- Segurança no GitHub: Deploy Keys individuais por repositório (somente leitura), remoção de credenciais expostas e acesso SSH via porta alternativa

🌱 Atualmente aprendendo

Aprofundando em containerização (Docker/Docker Compose), boas práticas de API REST e arquitetura de sistemas distribuídos, com o objetivo de evoluir para papéis backend com infraestrutura cloud.

🛠️ Stack principal

`PHP` `Laravel` `MySQL` `MariaDB` `SQL Server` `Linux (Debian)` `Apache` `Git/GitHub` `Tailwind CSS` `JavaScript`

📫 Contato

Aberto a oportunidades como Desenvolvedor Back-end PHP/Laravel. Entre em contato pelo [LinkedIn](https://linkedin.com/in/SEU-USUARIO-AQUI).
