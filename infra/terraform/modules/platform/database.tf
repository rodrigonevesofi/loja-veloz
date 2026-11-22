# PostgreSQL gerenciado (Amazon RDS): estado crítico fica FORA do cluster, com Multi-AZ,
# backups automáticos, criptografia em repouso e patching gerenciado.

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL acessivel apenas pelos nos do EKS"
  vpc_id      = module.vpc.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_nodes" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = module.eks.node_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_db_instance" "postgres" {
  identifier     = "${local.name}-pg"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage     = 50
  max_allocated_storage = 200
  storage_type          = "gp3"
  storage_encrypted     = true

  username                    = "veloz_admin"
  manage_master_user_password = true # senha gerada e rotacionada no Secrets Manager

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = var.db_multi_az
  publicly_accessible    = false

  backup_retention_period      = var.db_backup_retention_days
  deletion_protection          = var.environment == "prod"
  skip_final_snapshot          = var.environment != "prod"
  final_snapshot_identifier    = "${local.name}-pg-final"
  performance_insights_enabled = true
  auto_minor_version_upgrade   = true
}

# Uma credencial por serviço (database-per-service). Os usuários são criados no banco por um
# Job de migração; aqui ficam os segredos que o External Secrets entrega aos pods.
resource "random_password" "service_db" {
  for_each = toset(var.app_services_with_db)

  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "service_db" {
  for_each = toset(var.app_services_with_db)

  name                    = "loja-veloz/${var.environment}/${each.key}-db"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "service_db" {
  for_each = toset(var.app_services_with_db)

  secret_id = aws_secretsmanager_secret.service_db[each.key].id
  secret_string = jsonencode({
    username = each.key
    password = random_password.service_db[each.key].result
    host     = aws_db_instance.postgres.address
    dbname   = each.key
  })
}
