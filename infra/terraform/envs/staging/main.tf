# Raiz de STAGING: mesmo módulo de produção, dimensionado para custo baixo.
# Paridade dev/prod (12-Factor, fator X): a diferença entre ambientes são parâmetros, não código.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket       = "loja-veloz-terraform-state"
    key          = "staging/platform.tfstate"
    region       = "sa-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "sa-east-1"

  default_tags {
    tags = {
      Project     = "loja-veloz"
      Environment = "staging"
      ManagedBy   = "terraform"
      CostCenter  = "ecommerce"
    }
  }
}

module "platform" {
  source = "../../modules/platform"

  environment        = "staging"
  github_repository  = var.github_repository
  github_environment = "staging"

  # o provedor OIDC é único por conta; aqui assumimos staging e prod em contas separadas
  create_github_oidc_provider = true

  node_instance_types      = ["t3.large", "t3a.large"]
  node_min_size            = 2
  node_max_size            = 6
  node_desired_size        = 2
  db_instance_class        = "db.t4g.medium"
  db_multi_az              = false
  db_backup_retention_days = 3
}

variable "github_repository" {
  description = "owner/repo do GitHub autorizado a fazer deploy."
  type        = string
  default     = "loja-veloz/pedidos-veloz"
}

output "platform" {
  value = module.platform
}
