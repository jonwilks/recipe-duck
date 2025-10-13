# SES email identity (domain verification)
# Note: You must manually add the verification records to your DNS
resource "aws_ses_domain_identity" "main" {
  domain = var.domain_name
}

# Optional: DKIM for email authentication
resource "aws_ses_domain_dkim" "main" {
  domain = aws_ses_domain_identity.main.domain
}

# SES receipt rule set
resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "${var.project_name}-ruleset-${var.environment}"
}

# Set the rule set as active
resource "aws_ses_active_receipt_rule_set" "main" {
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
}

# SES receipt rule to save emails to S3 and trigger Lambda
resource "aws_ses_receipt_rule" "save_to_s3" {
  name          = "${var.project_name}-save-to-s3"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  recipients    = [var.deployment_email]
  enabled       = true
  scan_enabled  = true

  # Action 1: Save email to S3
  s3_action {
    bucket_name       = aws_s3_bucket.email_bucket.id
    position          = 1
    object_key_prefix = "emails/"
  }

  depends_on = [
    aws_s3_bucket_policy.email_bucket
  ]
}

# Output verification records for DNS configuration
output "ses_verification_token" {
  description = "SES domain verification token - Add this as a TXT record"
  value       = aws_ses_domain_identity.main.verification_token
}

output "ses_dkim_tokens" {
  description = "DKIM tokens for email authentication - Add these as CNAME records"
  value       = aws_ses_domain_dkim.main.dkim_tokens
}

output "ses_dns_instructions" {
  description = "DNS records needed for SES verification"
  value = <<-EOT
    DNS Records Required:
    ---------------------

    1. Domain Verification (TXT record):
       Name:  _amazonses.${var.domain_name}
       Type:  TXT
       Value: ${aws_ses_domain_identity.main.verification_token}

    2. DKIM Records (CNAME records):
       ${join("\n       ", [for token in aws_ses_domain_dkim.main.dkim_tokens : "${token}._domainkey.${var.domain_name} -> ${token}.dkim.amazonses.com"])}

    3. MX Record (for receiving emails):
       Name:  ${var.domain_name}
       Type:  MX
       Value: 10 inbound-smtp.${data.aws_region.current.name}.amazonaws.com

    After adding these records:
    - Wait for DNS propagation (can take up to 72 hours, usually much faster)
    - Check verification status in AWS SES Console
    - Test by sending an email to: ${var.deployment_email}
  EOT
}
