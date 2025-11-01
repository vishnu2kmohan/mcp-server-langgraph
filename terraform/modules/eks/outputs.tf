output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "cluster_platform_version" {
  description = "EKS cluster platform version"
  value       = aws_eks_cluster.main.platform_version
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_security_group.cluster.id
}

output "node_security_group_id" {
  description = "Security group ID attached to the EKS nodes"
  value       = aws_security_group.node.id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = try(aws_eks_cluster.main.identity[0].oidc[0].issuer, "")
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for EKS"
  value       = aws_iam_openid_connect_provider.cluster.arn
}

output "oidc_provider" {
  description = "OIDC provider without https:// prefix"
  value       = local.oidc_provider
}

#######################
# IAM Roles
#######################

output "cluster_iam_role_arn" {
  description = "IAM role ARN of the EKS cluster"
  value       = aws_iam_role.cluster.arn
}

output "cluster_iam_role_name" {
  description = "IAM role name of the EKS cluster"
  value       = aws_iam_role.cluster.name
}

output "node_iam_role_arn" {
  description = "IAM role ARN of the EKS nodes"
  value       = aws_iam_role.node.arn
}

output "node_iam_role_name" {
  description = "IAM role name of the EKS nodes"
  value       = aws_iam_role.node.name
}

output "vpc_cni_irsa_role_arn" {
  description = "IAM role ARN for VPC CNI addon"
  value       = aws_iam_role.vpc_cni.arn
}

output "ebs_csi_irsa_role_arn" {
  description = "IAM role ARN for EBS CSI driver"
  value       = try(aws_iam_role.ebs_csi[0].arn, "")
}

output "cluster_autoscaler_irsa_role_arn" {
  description = "IAM role ARN for Cluster Autoscaler"
  value       = try(aws_iam_role.cluster_autoscaler[0].arn, "")
}

output "application_irsa_role_arn" {
  description = "IAM role ARN for application pods"
  value       = try(aws_iam_role.application[0].arn, "")
}

output "application_irsa_role_name" {
  description = "IAM role name for application pods"
  value       = try(aws_iam_role.application[0].name, "")
}

#######################
# Node Groups
#######################

output "general_node_group_id" {
  description = "General node group ID"
  value       = try(aws_eks_node_group.general[0].id, "")
}

output "general_node_group_arn" {
  description = "General node group ARN"
  value       = try(aws_eks_node_group.general[0].arn, "")
}

output "general_node_group_status" {
  description = "General node group status"
  value       = try(aws_eks_node_group.general[0].status, "")
}

output "compute_node_group_id" {
  description = "Compute node group ID"
  value       = try(aws_eks_node_group.compute[0].id, "")
}

output "compute_node_group_arn" {
  description = "Compute node group ARN"
  value       = try(aws_eks_node_group.compute[0].arn, "")
}

output "spot_node_group_id" {
  description = "Spot node group ID"
  value       = try(aws_eks_node_group.spot[0].id, "")
}

output "spot_node_group_arn" {
  description = "Spot node group ARN"
  value       = try(aws_eks_node_group.spot[0].arn, "")
}

#######################
# Addons
#######################

output "vpc_cni_addon_version" {
  description = "Version of VPC CNI addon"
  value       = aws_eks_addon.vpc_cni.addon_version
}

output "coredns_addon_version" {
  description = "Version of CoreDNS addon"
  value       = aws_eks_addon.coredns.addon_version
}

output "kube_proxy_addon_version" {
  description = "Version of kube-proxy addon"
  value       = aws_eks_addon.kube_proxy.addon_version
}

output "ebs_csi_addon_version" {
  description = "Version of EBS CSI driver addon"
  value       = try(aws_eks_addon.ebs_csi_driver[0].addon_version, "")
}

#######################
# CloudWatch
#######################

output "cloudwatch_log_group_name" {
  description = "Name of CloudWatch log group for cluster logs"
  value       = aws_cloudwatch_log_group.cluster.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of CloudWatch log group for cluster logs"
  value       = aws_cloudwatch_log_group.cluster.arn
}

#######################
# Kubectl Configuration
#######################

output "kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.main.name}"
}
