
resource "aws_db_instance" "postgres" {
  identifier     = var.db_identifier
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = var.db_port

  publicly_accessible = true
  skip_final_snapshot = true
  apply_immediately   = true

  tags = {
    Environment = "local"
    ManagedBy   = "terraform"
    Project     = "my-project"
  }
}
