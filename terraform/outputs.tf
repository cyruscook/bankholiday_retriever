output "lambda_function_name" {
  description = "Name of the retriever Lambda function."
  value       = module.retriever_function.function_name
}

output "lambda_function_arn" {
  description = "ARN of the retriever Lambda function."
  value       = module.retriever_function.function_arn
}

output "s3_bucket_name" {
  description = "Effective S3 bucket name used by the Lambda."
  value       = local.s3_bucket_name
}

output "sns_topic_arn" {
  description = "Effective SNS topic ARN used by the Lambda."
  value       = local.sns_topic_arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role."
  value       = module.lambda_execution_role.role_arn
}
