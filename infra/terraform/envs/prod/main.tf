# Raiz de PRODUÇÃO. Cada ambiente tem seu próprio state (isolamento de falhas e de
# permissões): um `apply` em staging nunca toca produção.
#
#   terraform -chdir=infra/terraform/envs/prod init
#   terraform -chdir=infra/terraform/envs/prod plan -out=tfplan
#   terraform -chdir=infra/terraform/envs/prod apply tfplan

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

  # State remoto, criptografado e com lock nativo do S3 (use_lockfile, Terraform >= 1.10).
  # O bucket é criado uma única vez fora deste código (bootstrap), com versionamento ligado.
  backend "s3" {
    bucket       = "loja-veloz-terraform-state"
    key          = "prod/platform.tfstate"
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
      Environment = "prod"
      ManagedBy   = "terraform"
      CostCenter  = "ecommerce"
    }
  }
}

module "platform" {
  source = "../../modules/platform"

  environment        = "prod"
  github_repository  = var.github_repository
  github_environment = "production"

  node_instance_types      = ["m6i.xlarge", "m5.xlarge"]
  node_min_size            = 3
  node_max_size            = 15
  node_desired_size        = 4
  db_instance_class        = "db.m7g.large"
  db_multi_az              = true
  db_backup_retention_days = 14
}

variable "github_repository" {
  description = "owner/repo do GitHub autorizado a fazer deploy."
  type        = string
  default     = "loja-veloz/pedidos-veloz"
}

output "platform" {
  value = module.platform
}
