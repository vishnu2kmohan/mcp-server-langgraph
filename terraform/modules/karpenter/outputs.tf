# Karpenter Module Outputs

output "controller_role_arn" {
  description = "ARN of the Karpenter controller IAM role"
  value       = aws_iam_role.karpenter_controller.arn
}

output "node_role_arn" {
  description = "ARN of the Karpenter node IAM role"
  value       = aws_iam_role.karpenter_node.arn
}

output "node_instance_profile_name" {
  description = "Name of the Karpenter node instance profile"
  value       = aws_iam_instance_profile.karpenter_node.name
}

output "sqs_queue_name" {
  description = "Name of the Karpenter SQS queue for interruption handling"
  value       = aws_sqs_queue.karpenter.name
}

output "sqs_queue_arn" {
  description = "ARN of the Karpenter SQS queue"
  value       = aws_sqs_queue.karpenter.arn
}
