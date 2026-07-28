locals {
  ecr_region = try(
    regex(
      "^[0-9]{12}\\.dkr\\.ecr\\.([a-z0-9-]+)\\.amazonaws\\.com(\\.cn)?/.+@sha256:[0-9a-f]{64}$",
      var.ecr_image_uri,
    )[0],
    "",
  )

  s3_bucket_name = var.existing_s3_bucket_name != null ? var.existing_s3_bucket_name : module.storage_bucket[0].bucket_name

  sns_topic_arn = var.existing_sns_topic_arn != null ? var.existing_sns_topic_arn : module.error_notifications[0].topic_arn

  sns_region = try(
    regex("^arn:[^:]+:sns:([a-z0-9-]+):[0-9]{12}:[A-Za-z0-9_-]{1,256}$", local.sns_topic_arn)[0],
    null,
  )
}

module "storage_bucket" {
  count  = var.existing_s3_bucket_name == null ? 1 : 0
  source = "./modules/storage_bucket"

  name = var.name
  tags = var.tags
}

module "error_notifications" {
  count  = var.existing_sns_topic_arn == null ? 1 : 0
  source = "./modules/error_notifications"

  name = var.name
  tags = var.tags
}

module "lambda_execution_role" {
  source = "./modules/lambda_execution_role"

  name           = var.name
  s3_bucket_name = local.s3_bucket_name
  sns_topic_arn  = local.sns_topic_arn
  tags           = var.tags
}

module "retriever_function" {
  source = "./modules/retriever_function"

  name           = var.name
  image_uri      = var.ecr_image_uri
  role_arn       = module.lambda_execution_role.role_arn
  memory_size    = var.memory_size
  timeout        = var.timeout
  log_level      = var.log_level
  s3_bucket_name = local.s3_bucket_name
  sns_topic_arn  = local.sns_topic_arn
  ecr_region     = local.ecr_region
  sns_region     = local.sns_region
  tags           = var.tags
}
