output "cluster_name" {
  description = "Vai para a variável EKS_CLUSTER_NAME do GitHub Environment."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "github_deploy_role_arn" {
  description = "Vai para a variável AWS_DEPLOY_ROLE_ARN do GitHub Environment."
  value       = aws_iam_role.github_deploy.arn
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "rds_master_secret_arn" {
  description = "Segredo (gerenciado pelo RDS) com a senha do usuário administrador."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
