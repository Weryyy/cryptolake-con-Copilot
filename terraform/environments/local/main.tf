# Local environment - uses MinIO instead of AWS S3
# This file is a reference for local development setup via Terraform

terraform {
  required_version = ">= 1.8"
}

variable "environment" {
  default = "local"
}
