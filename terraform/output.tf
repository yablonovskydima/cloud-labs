
output "bucket_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.app.bucket
}

output "bucket_arn" {
  description = "ARN of the local S3 bucket"
  value       = aws_s3_bucket.app.arn
}

output "floci_endpoint" {
  description = "Local Floci endpoint"
  value       = var.floci_endpoint
}

output "lambda_function_name" {
  description = "Name of the file router Lambda"
  value       = aws_lambda_function.file_router.function_name
}
