# CloudWatch Logs group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-processor-${var.environment}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-lambda-logs"
  }
}

# IAM role for Lambda execution
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-role"
  }
}

# IAM policy for Lambda to write CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM policy for Lambda to read from S3
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${var.project_name}-lambda-s3-access-${var.environment}"
  description = "Allow Lambda to read and delete objects from email S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.email_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.email_bucket.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# Attach secrets access policy
resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_secrets_access.arn
}

# Lambda function
# Supports both ZIP deployment (legacy) and Container images (recommended for HEIC support)
resource "aws_lambda_function" "recipe_processor" {
  # Use container image if specified, otherwise fall back to ZIP
  image_uri        = var.lambda_image_uri != "" ? var.lambda_image_uri : null
  package_type     = var.lambda_image_uri != "" ? "Image" : "Zip"

  # ZIP-based deployment (only used if lambda_image_uri is not set)
  filename         = var.lambda_image_uri == "" ? "${path.module}/../lambda/lambda_deployment.zip" : null
  handler          = var.lambda_image_uri == "" ? "lambda_handler.lambda_handler" : null
  runtime          = var.lambda_image_uri == "" ? "python3.11" : null
  source_code_hash = var.lambda_image_uri == "" && fileexists("${path.module}/../lambda/lambda_deployment.zip") ? filebase64sha256("${path.module}/../lambda/lambda_deployment.zip") : null

  function_name    = "${var.project_name}-processor-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

  environment {
    variables = {
      ANTHROPIC_API_KEY_SECRET    = aws_secretsmanager_secret.anthropic_api_key.name
      NOTION_API_KEY_SECRET       = aws_secretsmanager_secret.notion_api_key.name
      NOTION_DATABASE_ID_SECRET   = aws_secretsmanager_secret.notion_database_id.name
      EMAIL_WHITELIST_SECRET      = aws_secretsmanager_secret.email_whitelist.name
      ANTHROPIC_MODEL            = var.anthropic_model
      DELETE_EMAILS_AFTER_PROCESSING = tostring(var.delete_emails_after_processing)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_s3,
    aws_iam_role_policy_attachment.lambda_secrets
  ]

  tags = {
    Name = "${var.project_name}-processor"
  }

  # Ignore changes to source_code_hash and image_uri to prevent Terraform drift
  # The Lambda code will be deployed separately via build scripts
  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename,
      image_uri
    ]
  }
}

# Permission for S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recipe_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.email_bucket.arn
}

# CloudWatch alarm for Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Lambda function has more than 5 errors in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.recipe_processor.function_name
  }

  tags = {
    Name = "${var.project_name}-lambda-errors-alarm"
  }
}
