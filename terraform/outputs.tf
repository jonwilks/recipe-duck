output "email_receiving_address" {
  description = "Email address to send recipes to"
  value       = var.deployment_email
}

output "s3_bucket_name" {
  description = "S3 bucket name for email storage"
  value       = aws_s3_bucket.email_bucket.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.recipe_processor.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.recipe_processor.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch Logs group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "ses_receipt_rule_set" {
  description = "SES receipt rule set name"
  value       = aws_ses_receipt_rule_set.main.rule_set_name
}

output "secrets_manager_arns" {
  description = "ARNs of secrets in Secrets Manager"
  value = {
    anthropic_api_key    = aws_secretsmanager_secret.anthropic_api_key.arn
    notion_api_key       = aws_secretsmanager_secret.notion_api_key.arn
    notion_database_id   = aws_secretsmanager_secret.notion_database_id.arn
    email_whitelist      = aws_secretsmanager_secret.email_whitelist.arn
  }
  sensitive = true
}

output "deployment_instructions" {
  description = "Next steps for deployment"
  value = <<-EOT
    Deployment Summary:
    -------------------
    1. Email Address: ${var.deployment_email}
    2. S3 Bucket: ${aws_s3_bucket.email_bucket.id}
    3. Lambda Function: ${aws_lambda_function.recipe_processor.function_name}

    Next Steps:
    -----------
    1. Verify your domain in SES: ${var.domain_name}
       - Go to SES Console > Verified Identities
       - Add DNS records to verify domain ownership

    2. Move SES out of sandbox mode (for production):
       - Request production access in SES Console
       - Otherwise, you can only receive from verified addresses

    3. Deploy Lambda code:
       - Run: cd ../lambda && ./build.sh
       - Upload lambda_deployment.zip via AWS Console or CLI

    4. Test by sending an email to: ${var.deployment_email}
       - Include a recipe image attachment or URL
       - Check CloudWatch Logs: ${aws_cloudwatch_log_group.lambda_logs.name}

    5. Monitor:
       - CloudWatch Logs: ${aws_cloudwatch_log_group.lambda_logs.name}
       - Lambda Metrics: AWS Console > Lambda > ${aws_lambda_function.recipe_processor.function_name}
  EOT
}
