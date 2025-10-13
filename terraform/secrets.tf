# Secrets Manager for storing API keys and configuration

# Anthropic API Key
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.project_name}/${var.environment}/anthropic-api-key"
  description             = "Anthropic API key for Claude"
  recovery_window_in_days = 7

  tags = {
    Name = "anthropic-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# Notion API Key
resource "aws_secretsmanager_secret" "notion_api_key" {
  name                    = "${var.project_name}/${var.environment}/notion-api-key"
  description             = "Notion API key"
  recovery_window_in_days = 7

  tags = {
    Name = "notion-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "notion_api_key" {
  secret_id     = aws_secretsmanager_secret.notion_api_key.id
  secret_string = var.notion_api_key
}

# Notion Database ID
resource "aws_secretsmanager_secret" "notion_database_id" {
  name                    = "${var.project_name}/${var.environment}/notion-database-id"
  description             = "Notion database ID for recipes"
  recovery_window_in_days = 7

  tags = {
    Name = "notion-database-id"
  }
}

resource "aws_secretsmanager_secret_version" "notion_database_id" {
  secret_id     = aws_secretsmanager_secret.notion_database_id.id
  secret_string = var.notion_database_id
}

# Email Whitelist
resource "aws_secretsmanager_secret" "email_whitelist" {
  name                    = "${var.project_name}/${var.environment}/email-whitelist"
  description             = "Comma-separated list of whitelisted sender emails"
  recovery_window_in_days = 7

  tags = {
    Name = "email-whitelist"
  }
}

resource "aws_secretsmanager_secret_version" "email_whitelist" {
  secret_id     = aws_secretsmanager_secret.email_whitelist.id
  secret_string = var.email_whitelist
}

# IAM policy for Lambda to read secrets
resource "aws_iam_policy" "lambda_secrets_access" {
  name        = "${var.project_name}-lambda-secrets-access-${var.environment}"
  description = "Allow Lambda to read secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.anthropic_api_key.arn,
          aws_secretsmanager_secret.notion_api_key.arn,
          aws_secretsmanager_secret.notion_database_id.arn,
          aws_secretsmanager_secret.email_whitelist.arn
        ]
      }
    ]
  })
}
