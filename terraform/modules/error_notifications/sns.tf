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
  description = "Name of the SNS topic."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the topic."
}

resource "aws_sns_topic" "this" {
  name = var.name
  tags = var.tags
}

output "topic_arn" {
  description = "ARN of the created SNS topic."
  value       = aws_sns_topic.this.arn
}
