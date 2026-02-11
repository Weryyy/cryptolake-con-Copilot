# Módulo para provisionar storage en AWS S3 (producción)
# En local usamos MinIO que es S3-compatible

variable "environment" {
  type = string
}

variable "project_name" {
  type    = string
  default = "cryptolake"
}

# S3 Buckets para cada capa del Lakehouse
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project_name}-${var.environment}-bronze"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "bronze"
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.project_name}-${var.environment}-silver"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "silver"
  }
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.project_name}-${var.environment}-gold"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "gold"
  }
}

# Lifecycle rules: mover datos viejos a storage más barato
resource "aws_s3_bucket_lifecycle_configuration" "bronze_lifecycle" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Versionado para Bronze (raw data protection)
resource "aws_s3_bucket_versioning" "bronze_versioning" {
  bucket = aws_s3_bucket.bronze.id

  versioning_configuration {
    status = "Enabled"
  }
}

output "bronze_bucket_name" {
  value = aws_s3_bucket.bronze.bucket
}

output "silver_bucket_name" {
  value = aws_s3_bucket.silver.bucket
}

output "gold_bucket_name" {
  value = aws_s3_bucket.gold.bucket
}
