# EKS Cluster Module
# Creates an EKS cluster with managed node groups, IRSA, and essential addons

locals {
  cluster_name = var.cluster_name

  common_tags = merge(
    var.tags,
    {
      "kubernetes.io/cluster/${local.cluster_name}" = "owned"
      ManagedBy                                       = "Terraform"
      Module                                          = "eks"
    }
  )

  # OIDC provider URL without https://
  oidc_provider = try(replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", ""), "")
}

#######################
# EKS Cluster
#######################

resource "aws_eks_cluster" "main" {
  name     = local.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = concat(var.public_subnet_ids, var.private_subnet_ids)
    endpoint_private_access = var.cluster_endpoint_private_access
    endpoint_public_access  = var.cluster_endpoint_public_access
    public_access_cidrs     = var.cluster_endpoint_public_access_cidrs
    security_group_ids      = [aws_security_group.cluster.id]
  }

  # Enable control plane logging
  enabled_cluster_log_types = var.cluster_enabled_log_types

  encryption_config {
    provider {
      key_arn = var.cluster_encryption_key_arn != null ? var.cluster_encryption_key_arn : aws_kms_key.eks[0].arn
    }
    resources = ["secrets"]
  }

  tags = merge(
    local.common_tags,
    {
      Name = local.cluster_name
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.cluster_vpc_resource_controller,
    aws_cloudwatch_log_group.cluster,
  ]
}

#######################
# CloudWatch Log Group
#######################

resource "aws_cloudwatch_log_group" "cluster" {
  name              = "/aws/eks/${local.cluster_name}/cluster"
  retention_in_days = var.cluster_log_retention_days
  kms_key_id        = var.cluster_log_kms_key_id

  tags = local.common_tags
}

#######################
# KMS Key for EKS
#######################

resource "aws_kms_key" "eks" {
  count = var.cluster_encryption_key_arn == null ? 1 : 0

  description             = "EKS Secret Encryption Key for ${local.cluster_name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-eks-secrets"
    }
  )
}

resource "aws_kms_alias" "eks" {
  count = var.cluster_encryption_key_arn == null ? 1 : 0

  name          = "alias/${local.cluster_name}-eks-secrets"
  target_key_id = aws_kms_key.eks[0].key_id
}

#######################
# OIDC Provider (for IRSA)
#######################

data "tls_certificate" "cluster" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-oidc"
    }
  )
}

#######################
# Managed Node Groups
#######################

resource "aws_eks_node_group" "general" {
  count = var.enable_general_node_group ? 1 : 0

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.cluster_name}-general"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = var.kubernetes_version

  scaling_config {
    desired_size = var.general_node_group_desired_size
    max_size     = var.general_node_group_max_size
    min_size     = var.general_node_group_min_size
  }

  update_config {
    max_unavailable_percentage = 33
  }

  instance_types = var.general_node_group_instance_types
  capacity_type  = var.general_node_group_capacity_type
  disk_size      = var.general_node_group_disk_size

  labels = merge(
    var.general_node_group_labels,
    {
      "node.kubernetes.io/node-group" = "general"
      "workload-type"                  = "general"
    }
  )

  dynamic "taint" {
    for_each = var.general_node_group_taints
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = merge(
    local.common_tags,
    var.general_node_group_tags,
    {
      Name = "${local.cluster_name}-general-node"
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.node_policy,
    aws_iam_role_policy_attachment.node_cni_policy,
    aws_iam_role_policy_attachment.node_ecr_policy,
  ]

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "compute" {
  count = var.enable_compute_node_group ? 1 : 0

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.cluster_name}-compute"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = var.kubernetes_version

  scaling_config {
    desired_size = var.compute_node_group_desired_size
    max_size     = var.compute_node_group_max_size
    min_size     = var.compute_node_group_min_size
  }

  update_config {
    max_unavailable_percentage = 33
  }

  instance_types = var.compute_node_group_instance_types
  capacity_type  = var.compute_node_group_capacity_type
  disk_size      = var.compute_node_group_disk_size

  labels = merge(
    var.compute_node_group_labels,
    {
      "node.kubernetes.io/node-group" = "compute"
      "workload-type"                  = "compute-intensive"
    }
  )

  dynamic "taint" {
    for_each = var.compute_node_group_taints
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = merge(
    local.common_tags,
    var.compute_node_group_tags,
    {
      Name = "${local.cluster_name}-compute-node"
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.node_policy,
    aws_iam_role_policy_attachment.node_cni_policy,
    aws_iam_role_policy_attachment.node_ecr_policy,
  ]

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "spot" {
  count = var.enable_spot_node_group ? 1 : 0

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.cluster_name}-spot"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = var.kubernetes_version

  scaling_config {
    desired_size = var.spot_node_group_desired_size
    max_size     = var.spot_node_group_max_size
    min_size     = var.spot_node_group_min_size
  }

  update_config {
    max_unavailable_percentage = 50 # Spot instances can be interrupted
  }

  instance_types = var.spot_node_group_instance_types
  capacity_type  = "SPOT"
  disk_size      = var.spot_node_group_disk_size

  labels = merge(
    var.spot_node_group_labels,
    {
      "node.kubernetes.io/node-group" = "spot"
      "workload-type"                  = "fault-tolerant"
      "karpenter.sh/capacity-type"     = "spot"
    }
  )

  # Taint spot nodes so only tolerant workloads run there
  taint {
    key    = "spot"
    value  = "true"
    effect = "NoSchedule"
  }

  dynamic "taint" {
    for_each = var.spot_node_group_taints
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = merge(
    local.common_tags,
    var.spot_node_group_tags,
    {
      Name                                            = "${local.cluster_name}-spot-node"
      "k8s.io/cluster-autoscaler/enabled"             = "true"
      "k8s.io/cluster-autoscaler/${local.cluster_name}" = "owned"
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.node_policy,
    aws_iam_role_policy_attachment.node_cni_policy,
    aws_iam_role_policy_attachment.node_ecr_policy,
  ]

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

#######################
# EKS Addons
#######################

resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "vpc-cni"
  addon_version            = var.vpc_cni_addon_version
  service_account_role_arn = aws_iam_role.vpc_cni.arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-vpc-cni"
    }
  )
}

resource "aws_eks_addon" "coredns" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "coredns"
  addon_version            = var.coredns_addon_version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-coredns"
    }
  )

  depends_on = [
    aws_eks_node_group.general,
    aws_eks_node_group.compute,
  ]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "kube-proxy"
  addon_version            = var.kube_proxy_addon_version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-kube-proxy"
    }
  )
}

resource "aws_eks_addon" "ebs_csi_driver" {
  count = var.enable_ebs_csi_driver ? 1 : 0

  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = var.ebs_csi_driver_version
  service_account_role_arn = aws_iam_role.ebs_csi[0].arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-ebs-csi"
    }
  )
}

#######################
# Security Groups
#######################

resource "aws_security_group" "cluster" {
  name_prefix = "${local.cluster_name}-cluster-"
  description = "EKS cluster security group"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-cluster-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "cluster_egress" {
  description       = "Allow all egress traffic"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.cluster.id
}

resource "aws_security_group_rule" "cluster_ingress_nodes" {
  description              = "Allow nodes to communicate with cluster API"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.node.id
  security_group_id        = aws_security_group.cluster.id
}

resource "aws_security_group" "node" {
  name_prefix = "${local.cluster_name}-node-"
  description = "EKS node security group"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name                                            = "${local.cluster_name}-node-sg"
      "kubernetes.io/cluster/${local.cluster_name}" = "owned"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "node_ingress_self" {
  description              = "Allow nodes to communicate with each other"
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  source_security_group_id = aws_security_group.node.id
  security_group_id        = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_ingress_cluster" {
  description              = "Allow cluster to communicate with nodes"
  type                     = "ingress"
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.cluster.id
  security_group_id        = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_ingress_cluster_kubelet" {
  description              = "Allow cluster to communicate with kubelet"
  type                     = "ingress"
  from_port                = 10250
  to_port                  = 10250
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.cluster.id
  security_group_id        = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_egress" {
  description       = "Allow all egress traffic"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.node.id
}
