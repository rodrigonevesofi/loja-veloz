# Rede + cluster Kubernetes gerenciado (EKS).
# Módulos oficiais da comunidade (terraform-aws-modules) com versão fixada: menos código
# próprio para manter e defaults já revisados por milhares de usuários.

locals {
  name = "loja-veloz-${var.environment}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name = local.name
  cidr = var.vpc_cidr
  azs  = var.azs

  # /20 por AZ: espaço de sobra para o VPC CNI (cada pod recebe um IP da VPC)
  private_subnets  = [for i, _ in var.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets   = [for i, _ in var.azs : cidrsubnet(var.vpc_cidr, 8, 48 + i)]
  database_subnets = [for i, _ in var.azs : cidrsubnet(var.vpc_cidr, 8, 64 + i)]

  create_database_subnet_group = true
  enable_nat_gateway           = true
  single_nat_gateway           = var.environment != "prod" # prod: um NAT por AZ (sem SPOF)
  enable_dns_hostnames         = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = local.name
  cluster_version = var.kubernetes_version

  cluster_endpoint_public_access           = true
  cluster_endpoint_public_access_cidrs     = var.api_allowed_cidrs
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_addons = {
    coredns                = {}
    kube-proxy             = {}
    eks-pod-identity-agent = {}
    metrics-server         = {} # fonte de CPU/memória para o HPA
    aws-ebs-csi-driver     = {}
    vpc-cni = {
      before_compute = true

      # sem isto as NetworkPolicies seriam aceitas pela API mas NÃO aplicadas
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
  }

  eks_managed_node_groups = {
    app = {
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size
      labels = {
        workload = "app"
      }
    }
  }

  # O pipeline só ganha permissão de edição no namespace da aplicação (menor privilégio).
  access_entries = {
    github_deploy = {
      principal_arn = aws_iam_role.github_deploy.arn
      policy_associations = {
        app = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = {
            type       = "namespace"
            namespaces = ["loja-veloz"]
          }
        }
      }
    }
  }
}
