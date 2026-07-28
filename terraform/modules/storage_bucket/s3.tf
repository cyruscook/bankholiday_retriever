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
  description = "Base name for the bucket."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the bucket."
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  bucket_name = format(
    "%s-%s-%s-an",
    var.name,
    data.aws_caller_identity.current.account_id,
    data.aws_region.current.region,
  )
}

resource "aws_s3_bucket" "this" {
  bucket           = local.bucket_name
  bucket_namespace = "account-regional"
  force_destroy    = false
  tags             = var.tags
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  description = "Name of the created S3 bucket."
  value       = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  description = "ARN of the created S3 bucket."
  value       = aws_s3_bucket.this.arn
}
