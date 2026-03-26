1. Criar servidor Linux
2. Clonar projeto em /srv/rdc_inteligente
3. Criar venv e instalar requirements
4. Configurar variaveis de ambiente
5. Rodar migrate
6. Rodar collectstatic
7. Copiar rdc_inteligente.service para /etc/systemd/system/
8. Copiar rdc_inteligente.nginx para /etc/nginx/sites-available/
9. Habilitar site no nginx
10. systemctl daemon-reload
11. systemctl enable rdc_inteligente
12. systemctl start rdc_inteligente
13. systemctl restart nginx

