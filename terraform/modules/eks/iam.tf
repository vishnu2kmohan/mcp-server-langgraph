# IAM roles and policies for EKS cluster, nodes, and IRSA

#######################
# Cluster IAM Role
#######################

resource "aws_iam_role" "cluster" {
  name_prefix = "${local.cluster_name}-cluster-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-cluster-role"
    }
  )
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "cluster_vpc_resource_controller" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
}

#######################
# Node IAM Role
#######################

resource "aws_iam_role" "node" {
  name_prefix = "${local.cluster_name}-node-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-node-role"
    }
  )
}

resource "aws_iam_role_policy_attachment" "node_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "node_cni_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "node_ecr_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Additional policy for SSM access (for debugging)
resource "aws_iam_role_policy_attachment" "node_ssm_policy" {
  count = var.enable_ssm_access ? 1 : 0

  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# CloudWatch metrics and logs
resource "aws_iam_role_policy_attachment" "node_cloudwatch_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

#######################
# VPC CNI IRSA Role
#######################

resource "aws_iam_role" "vpc_cni" {
  name_prefix = "${local.cluster_name}-vpc-cni-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_provider}:aud" = "sts.amazonaws.com"
            "${local.oidc_provider}:sub" = "system:serviceaccount:kube-system:aws-node"
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-vpc-cni-irsa"
    }
  )
}

resource "aws_iam_role_policy_attachment" "vpc_cni" {
  role       = aws_iam_role.vpc_cni.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

#######################
# EBS CSI Driver IRSA Role
#######################

resource "aws_iam_role" "ebs_csi" {
  count = var.enable_ebs_csi_driver ? 1 : 0

  name_prefix = "${local.cluster_name}-ebs-csi-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_provider}:aud" = "sts.amazonaws.com"
            "${local.oidc_provider}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-ebs-csi-irsa"
    }
  )
}

resource "aws_iam_policy" "ebs_csi" {
  count = var.enable_ebs_csi_driver ? 1 : 0

  name_prefix = "${local.cluster_name}-ebs-csi-"
  description = "EBS CSI driver policy for ${local.cluster_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read-only Describe actions require Resource = "*" (AWS IAM limitation)
      # These cannot be scoped to specific ARNs by AWS design
      {
        Sid    = "EBSCSIDescribeActions"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumesModifications"
        ]
        Resource = "*"
      },
      # Mutating actions scoped to account and cluster-tagged resources
      # CKV_AWS_290/CKV_AWS_355: Scoped by account + cluster tag condition
      {
        Sid    = "EBSCSIMutatingActions"
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:ModifyVolume"
        ]
        Resource = [
          "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:volume/*",
          "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:snapshot/*",
          "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:instance/*"
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceTag/kubernetes.io/cluster/${var.cluster_name}" = "owned"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateTags"
        ]
        Resource = [
          "arn:aws:ec2:*:*:volume/*",
          "arn:aws:ec2:*:*:snapshot/*"
        ]
        Condition = {
          StringEquals = {
            "ec2:CreateAction" = [
              "CreateVolume",
              "CreateSnapshot"
            ]
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteTags"
        ]
        Resource = [
          "arn:aws:ec2:*:*:volume/*",
          "arn:aws:ec2:*:*:snapshot/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateVolume"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "aws:RequestTag/ebs.csi.aws.com/cluster" = "true"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateVolume"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "aws:RequestTag/CSIVolumeName" = "*"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteVolume"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ec2:ResourceTag/ebs.csi.aws.com/cluster" = "true"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteVolume"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ec2:ResourceTag/CSIVolumeName" = "*"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteVolume"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ec2:ResourceTag/kubernetes.io/created-for/pvc/name" = "*"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteSnapshot"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ec2:ResourceTag/CSIVolumeSnapshotName" = "*"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DeleteSnapshot"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ec2:ResourceTag/ebs.csi.aws.com/cluster" = "true"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  count = var.enable_ebs_csi_driver ? 1 : 0

  role       = aws_iam_role.ebs_csi[0].name
  policy_arn = aws_iam_policy.ebs_csi[0].arn
}

#######################
# Cluster Autoscaler IRSA Role
#######################

resource "aws_iam_role" "cluster_autoscaler" {
  count = var.enable_cluster_autoscaler_irsa ? 1 : 0

  name_prefix = "${local.cluster_name}-cluster-autoscaler-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_provider}:aud" = "sts.amazonaws.com"
            "${local.oidc_provider}:sub" = "system:serviceaccount:kube-system:cluster-autoscaler"
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-cluster-autoscaler-irsa"
    }
  )
}

resource "aws_iam_policy" "cluster_autoscaler" {
  count = var.enable_cluster_autoscaler_irsa ? 1 : 0

  name_prefix = "${local.cluster_name}-cluster-autoscaler-"
  description = "Cluster Autoscaler policy for ${local.cluster_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeLaunchTemplateVersions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "autoscaling:ResourceTag/k8s.io/cluster-autoscaler/${local.cluster_name}" = "owned"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "cluster_autoscaler" {
  count = var.enable_cluster_autoscaler_irsa ? 1 : 0

  role       = aws_iam_role.cluster_autoscaler[0].name
  policy_arn = aws_iam_policy.cluster_autoscaler[0].arn
}

#######################
# Application IRSA Role
#######################

resource "aws_iam_role" "application" {
  count = var.create_application_irsa_role ? 1 : 0

  name_prefix = "${local.cluster_name}-app-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_provider}:aud" = "sts.amazonaws.com"
            "${local.oidc_provider}:sub" = var.application_service_account_namespace != "" ? "system:serviceaccount:${var.application_service_account_namespace}:${var.application_service_account_name}" : "system:serviceaccount:default:mcp-server-langgraph"
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_name}-app-irsa"
    }
  )
}

resource "aws_iam_policy" "application_secrets" {
  # Only create if IRSA role is enabled AND at least one ARN list is non-empty
  count = var.create_application_irsa_role && (length(var.application_secrets_arns) > 0 || length(var.application_kms_key_arns) > 0) ? 1 : 0

  name_prefix = "${local.cluster_name}-app-secrets-"
  description = "Application Secrets Manager access for ${local.cluster_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # Secrets Manager access (only if ARNs are specified)
      length(var.application_secrets_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = var.application_secrets_arns
        }
      ] : [],
      # KMS access (only if ARNs are specified)
      length(var.application_kms_key_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "kms:Decrypt",
            "kms:DescribeKey"
          ]
          Resource = var.application_kms_key_arns
        }
      ] : []
    )
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "application_secrets" {
  # Only attach if the policy was created (matching the policy's count condition)
  count = var.create_application_irsa_role && (length(var.application_secrets_arns) > 0 || length(var.application_kms_key_arns) > 0) ? 1 : 0

  role       = aws_iam_role.application[0].name
  policy_arn = aws_iam_policy.application_secrets[0].arn
}

# CloudWatch Logs policy for application
resource "aws_iam_policy" "application_logs" {
  count = var.create_application_irsa_role ? 1 : 0

  name_prefix = "${local.cluster_name}-app-logs-"
  description = "CloudWatch Logs access for ${local.cluster_name} application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/eks/${local.cluster_name}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "application_logs" {
  count = var.create_application_irsa_role ? 1 : 0

  role       = aws_iam_role.application[0].name
  policy_arn = aws_iam_policy.application_logs[0].arn
}

# X-Ray policy for application
resource "aws_iam_policy" "application_xray" {
  count = var.create_application_irsa_role && var.enable_xray ? 1 : 0

  name_prefix = "${local.cluster_name}-app-xray-"
  description = "X-Ray access for ${local.cluster_name} application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "application_xray" {
  count = var.create_application_irsa_role && var.enable_xray ? 1 : 0

  role       = aws_iam_role.application[0].name
  policy_arn = aws_iam_policy.application_xray[0].arn
}

# Data sources
data "aws_caller_identity" "current" {}
