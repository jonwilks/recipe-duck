variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "deployment_email" {
  description = "Email address for SES to receive recipe emails (e.g., recipes@yourdomain.com)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for SES email receiving (must match deployment_email domain)"
  type        = string
}

variable "email_whitelist" {
  description = "Comma-separated list of allowed sender emails (supports wildcards like *@example.com)"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "notion_api_key" {
  description = "Notion API key"
  type        = string
  sensitive   = true
}

variable "notion_database_id" {
  description = "Notion database ID for storing recipes"
  type        = string
  sensitive   = true
}

variable "anthropic_model" {
  description = "Claude model to use for recipe processing"
  type        = string
  default     = "claude-haiku-4-5"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300 # 5 minutes
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "email_retention_days" {
  description = "Number of days to retain emails in S3 before deletion"
  type        = number
  default     = 1
}

variable "delete_emails_after_processing" {
  description = "Whether to delete emails from S3 immediately after processing"
  type        = bool
  default     = true
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "recipe-duck"
}

variable "lambda_image_uri" {
  description = "Lambda container image URI from ECR (set after building container image)"
  type        = string
  default     = ""
}
