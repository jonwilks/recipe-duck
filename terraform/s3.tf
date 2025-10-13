# S3 bucket for storing incoming emails from SES
resource "aws_s3_bucket" "email_bucket" {
  bucket = "${var.project_name}-emails-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.project_name}-emails"
    Description = "Storage for incoming recipe emails from SES"
  }
}

# Block all public access to email bucket
resource "aws_s3_bucket_public_access_block" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy to delete old emails
resource "aws_s3_bucket_lifecycle_configuration" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id

  rule {
    id     = "delete-old-emails"
    status = "Enabled"

    filter {
      prefix = "emails/"
    }

    expiration {
      days = var.email_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# Bucket policy to allow SES to write emails
resource "aws_s3_bucket_policy" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSESPuts"
        Effect = "Allow"
        Principal = {
          Service = "ses.amazonaws.com"
        }
        Action = "s3:PutObject"
        Resource = "${aws_s3_bucket.email_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          StringLike = {
            "AWS:SourceArn" = "arn:aws:ses:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:receipt-rule-set/*"
          }
        }
      }
    ]
  })
}

# S3 bucket notification to trigger Lambda on new objects
resource "aws_s3_bucket_notification" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.recipe_processor.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
