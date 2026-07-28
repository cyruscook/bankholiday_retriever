variable "ecr_image_uri" {
  type        = string
  description = "Digest-pinned, same-Region ECR image URI for the ARM64 Lambda image."

  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.([a-z0-9-]+)\\.amazonaws\\.com(\\.cn)?/.+@sha256:[0-9a-f]{64}$", var.ecr_image_uri))
    error_message = "ecr_image_uri must be a digest-pinned ECR URI with a 12-digit account ID and lowercase Region."
  }
}

variable "existing_s3_bucket_name" {
  type        = string
  default     = null
  nullable    = true
  description = "Existing S3 bucket to reference instead of creating one."

  validation {
    condition     = var.existing_s3_bucket_name == null || can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.existing_s3_bucket_name))
    error_message = "existing_s3_bucket_name must be null or 3-63 lowercase characters, numbers, periods, and hyphens, starting and ending with a letter or number."
  }

  validation {
    condition     = var.existing_s3_bucket_name == null || !strcontains(var.existing_s3_bucket_name, "..")
    error_message = "existing_s3_bucket_name must not contain adjacent periods."
  }

  validation {
    condition     = var.existing_s3_bucket_name == null || !can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$", var.existing_s3_bucket_name))
    error_message = "existing_s3_bucket_name must not be formatted as an IPv4 address."
  }
}

variable "existing_sns_topic_arn" {
  type        = string
  default     = null
  nullable    = true
  description = "Existing standard SNS topic ARN to reference instead of creating one."

  validation {
    condition     = var.existing_sns_topic_arn == null || can(regex("^arn:[^:]+:sns:([a-z0-9-]+):[0-9]{12}:[A-Za-z0-9_-]{1,256}$", var.existing_sns_topic_arn))
    error_message = "existing_sns_topic_arn must be null or a standard SNS topic ARN."
  }
}

variable "name" {
  type        = string
  default     = "bankholiday-retriever"
  description = "Lowercase name used for created AWS resources."

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,22}[a-z0-9])?$", var.name))
    error_message = "name must be 1-24 lowercase letters, numbers, or hyphens, and must start and end with a letter or number."
  }
}

variable "log_level" {
  type        = string
  default     = "INFO"
  description = "Application log level."

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], upper(var.log_level))
    error_message = "log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL, case-insensitively."
  }
}

variable "memory_size" {
  type        = number
  default     = 512
  description = "Lambda memory size in MB."

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 32768
    error_message = "memory_size must be between 128 and 32768 MB."
  }
}

variable "timeout" {
  type        = number
  default     = 900
  description = "Lambda timeout in seconds."

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "timeout must be between 1 and 900 seconds."
  }
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to created taggable resources."
}
