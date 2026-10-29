
resource "aws_s3_bucket" "app" {
  bucket = var.bucket_name

  tags = {
    Environment = "local"
    ManagedBy   = "terraform"
    Project     = "my-project"
  }
}

resource "aws_s3_object" "folders" {
  for_each = toset(["incoming/", "processed/", "ignored/"])

  bucket  = aws_s3_bucket.app.id
  key     = each.value
  content = ""
}
