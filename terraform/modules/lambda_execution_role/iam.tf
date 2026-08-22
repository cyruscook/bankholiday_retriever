terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.56"
    }
  }
}

variable "name" {
  type        = string
  description = "Base name for the Lambda resources."
}

variable "s3_bucket_name" {
  type        = string
  description = "Effective S3 bucket name used by the Lambda."
}

variable "sns_topic_arn" {
  type        = string
  description = "Effective SNS topic ARN used by the Lambda."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the IAM role."
}

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}
data "aws_service_principal" "lambda" {
  service_name = "lambda"
}

locals {
  log_group_arn = format(
    "arn:%s:logs:%s:%s:log-group:/aws/lambda/%s",
    data.aws_partition.current.partition,
    data.aws_region.current.region,
    data.aws_caller_identity.current.account_id,
    var.name,
  )
  s3_bucket_arn = format("arn:%s:s3:::%s", data.aws_partition.current.partition, var.s3_bucket_name)
}

resource "aws_iam_role" "lambda" {
  name = format("%s-lambda", var.name)
  tags = var.tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = data.aws_service_principal.lambda.name
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = format("%s-lambda", var.name)
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "logs:CreateLogGroup"
        Resource = local.log_group_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = [
          local.log_group_arn,
          "${local.log_group_arn}:*",
        ]
      },
      {
        Effect = "Allow"
        Action = "s3:PutObject"
        Resource = [
          "${local.s3_bucket_arn}/proclaimed_bhs.json",
          "${local.s3_bucket_arn}/proclaimed_not_bhs.json",
        ]
      },
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = var.sns_topic_arn
      },
    ]
  })
}

output "role_arn" {
  description = "ARN of the Lambda execution role."
  value       = aws_iam_role.lambda.arn
}
