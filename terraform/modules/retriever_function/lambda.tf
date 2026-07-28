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
  description = "Name of the Lambda function."
}

variable "image_uri" {
  type        = string
  description = "Digest-pinned ECR image URI."
}

variable "role_arn" {
  type        = string
  description = "ARN of the Lambda execution role."
}

variable "memory_size" {
  type        = number
  description = "Lambda memory size in MB."
}

variable "timeout" {
  type        = number
  description = "Lambda timeout in seconds."
}

variable "log_level" {
  type        = string
  description = "Application log level."
}

variable "s3_bucket_name" {
  type        = string
  description = "Effective S3 bucket name used by the Lambda."
}

variable "sns_topic_arn" {
  type        = string
  description = "Effective SNS topic ARN used by the Lambda."
}

variable "ecr_region" {
  type        = string
  description = "Region parsed from the ECR image URI."
}

variable "sns_region" {
  type        = string
  nullable    = true
  description = "Region parsed from the SNS topic ARN."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the Lambda function."
}

data "aws_region" "current" {}

resource "aws_lambda_function" "this" {
  function_name = var.name
  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["arm64"]
  role          = var.role_arn
  memory_size   = var.memory_size
  timeout       = var.timeout
  tags          = var.tags

  environment {
    variables = {
      LOGLEVEL  = upper(var.log_level)
      S3_BUCKET = var.s3_bucket_name
      SNS_TOPIC = var.sns_topic_arn
    }
  }

  lifecycle {
    precondition {
      condition     = var.ecr_region == data.aws_region.current.region
      error_message = "The ECR image Region must match the Lambda provider Region."
    }

    precondition {
      condition     = var.sns_region == null || var.sns_region == data.aws_region.current.region
      error_message = "The SNS topic Region must match the Lambda provider Region."
    }
  }
}

output "function_name" {
  description = "Name of the Lambda function."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function."
  value       = aws_lambda_function.this.arn
}
