variable "environment" {
  description = "Environment name (local, dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "cryptolake"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
