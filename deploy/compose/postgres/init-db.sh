#!/bin/sh
# Executado pelo entrypoint oficial do postgres apenas na PRIMEIRA inicialização do volume.
# Database-per-service: cada serviço tem seu banco e seu usuário, sem acesso cruzado.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER pedidos WITH PASSWORD '${PEDIDOS_DB_PASSWORD}';
	CREATE DATABASE pedidos OWNER pedidos;
	REVOKE ALL ON DATABASE pedidos FROM PUBLIC;

	CREATE USER estoque WITH PASSWORD '${ESTOQUE_DB_PASSWORD}';
	CREATE DATABASE estoque OWNER estoque;
	REVOKE ALL ON DATABASE estoque FROM PUBLIC;
EOSQL
