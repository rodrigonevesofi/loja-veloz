variable "environment" {
  description = "Nome do ambiente (staging ou prod)."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment deve ser staging ou prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR da VPC. Precisa casar com o ipBlock do PostgreSQL nas NetworkPolicies."
  type        = string
  default     = "10.20.0.0/16"
}

variable "azs" {
  description = "Zonas de disponibilidade (3 para tolerar a perda de uma zona)."
  type        = list(string)
  default     = ["sa-east-1a", "sa-east-1b", "sa-east-1c"]
}

variable "kubernetes_version" {
  description = "Versão do Kubernetes no EKS."
  type        = string
  default     = "1.31"
}

variable "api_allowed_cidrs" {
  description = "CIDRs autorizados a falar com o endpoint público da API do EKS."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  description = "Tipos de instância do node group (mais de um aumenta a chance de capacidade)."
  type        = list(string)
  default     = ["m6i.large", "m5.large"]
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 10
}

variable "node_desired_size" {
  type    = number
  default = 3
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_multi_az" {
  description = "Réplica síncrona em outra AZ com failover automático."
  type        = bool
  default     = true
}

variable "db_backup_retention_days" {
  type    = number
  default = 7
}

variable "github_repository" {
  description = "Repositório autorizado a fazer deploy via OIDC (formato owner/repo)."
  type        = string
}

variable "github_environment" {
  description = "GitHub Environment autorizado (o token OIDC carrega esse claim)."
  type        = string
}

variable "create_github_oidc_provider" {
  description = "O provedor OIDC é único por conta AWS: crie em apenas um dos ambientes da conta."
  type        = bool
  default     = true
}

variable "app_services_with_db" {
  description = "Serviços que recebem banco e usuário próprios (database-per-service)."
  type        = list(string)
  default     = ["pedidos", "estoque"]
}
