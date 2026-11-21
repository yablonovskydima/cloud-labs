
variable "aws_region" {
  description = "AWS region used by the local emulator"
  type        = string
  default     = "us-east-1"
}

variable "floci_endpoint" {
  description = "Local Floci API endpoint"
  type        = string
  default     = "http://localhost:4566"
}

variable "bucket_name" {
  description = "Name of the local S3 bucket"
  type        = string
  default     = "my-project-bucket"
}

variable "lambda_name" {
  description = "Name of the Lambda function that routes incoming files"
  type        = string
  default     = "file-router"
}

variable "lambda_s3_endpoint" {
  description = "S3 endpoint as seen from inside the Lambda container"
  type        = string
  default     = "http://floci:4566"
}

variable "csv_pattern" {
  description = "Regex for valid .csv file names (e.g. city_routes_20261120.csv)"
  type        = string
  default     = "^city_routes_\\d{8}\\.csv$"
}

variable "json_pattern" {
  description = "Regex for valid .json file names (e.g. agri_enterprises_20261120.json)"
  type        = string
  default     = "^agri_enterprises_\\d{8}\\.json$"
}

variable "db_identifier" {
  description = "RDS instance identifier"
  type        = string
  default     = "my-project-db"
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "opendata"
}

variable "db_username" {
  description = "Master user of the PostgreSQL instance"
  type        = string
  default     = "labadmin"
}

variable "db_password" {
  description = "Master password (local emulator only)"
  type        = string
  default     = "labpassword"
  sensitive   = true
}

variable "db_port" {
  description = "Port of the RDS proxy (Floci accepts 7001-7099)"
  type        = number
  default     = 7001
}

variable "lambda_db_host" {
  description = "RDS host as seen from inside the Lambda container (Floci RDS proxy)"
  type        = string
  default     = "floci"
}
