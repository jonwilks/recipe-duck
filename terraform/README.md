# Terraform Infrastructure

This directory contains Terraform configuration for deploying Recipe Duck's AWS infrastructure.

## Architecture

The infrastructure creates a serverless email-to-Notion pipeline:

```
Email -> Route53 (DNS) -> SES -> S3 -> Lambda -> Notion
                                  |
                                  +-> CloudWatch Logs
```

**Components:**
- **Amazon SES** - Receives emails at your domain
- **S3 Bucket** - Stores incoming emails temporarily
- **Lambda Function** - Processes recipes and pushes to Notion
- **ECR Repository** - Stores Lambda container images
- **Secrets Manager** - Securely stores API keys and configuration
- **CloudWatch** - Logs and monitoring
- **IAM Roles** - Permissions for Lambda execution

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Domain name** that you control (for email receiving)
3. **Terraform** installed (v1.0+)
4. **AWS CLI** configured with credentials
5. **Anthropic API key** (from console.anthropic.com)
6. **Notion integration** (API key and database ID)

## Quick Start

### 1. Configure Variables

Create your configuration file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required: Your AWS region
aws_region = "us-east-1"

# Required: Email domain (must be a domain you own)
domain_name = "yourdomain.com"

# Required: Comma-separated list of allowed sender emails
email_whitelist = "you@gmail.com,friend@example.com"

# Required: API Keys (will be stored in AWS Secrets Manager)
anthropic_api_key = "sk-ant-..."
notion_api_key = "ntn_..."
notion_database_id = "abc123..."

# Optional: Lambda container image URI (set after building image)
# lambda_image_uri = "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/recipe-duck-lambda:latest"

# Optional: Environment (default: "prod")
# environment = "prod"

# Optional: AI model (default: "claude-3-5-sonnet-20241022")
# anthropic_model = "claude-3-5-sonnet-20241022"
```

### 2. Initialize Terraform

```bash
terraform init
```

This downloads required providers and initializes the backend.

### 3. Deploy Infrastructure

```bash
terraform plan    # Review changes
terraform apply   # Deploy infrastructure
```

This creates all AWS resources. Note the outputs, especially:
- S3 bucket name
- Lambda function name
- ECR repository URI

### 4. Configure DNS

After Terraform completes, you must configure your domain's DNS records:

**a) Get verification token:**
```bash
terraform output ses_verification_token
```

**b) Add TXT record to your domain:**
```
Name: _amazonses.yourdomain.com
Type: TXT
Value: [token from step a]
```

**c) Add MX record for email receiving:**
```
Name: yourdomain.com (or subdomain if using one)
Type: MX
Priority: 10
Value: inbound-smtp.us-east-1.amazonaws.com
```

**d) Wait for verification (can take up to 72 hours):**
```bash
aws ses get-identity-verification-attributes \
  --identities yourdomain.com \
  --region us-east-1
```

Look for `"VerificationStatus": "Success"`.

### 5. Deploy Lambda Function

See [lambda/README.md](../lambda/README.md) for Lambda deployment instructions.

```bash
cd ../lambda
./build_and_push_container.sh

# After image is built, update terraform.tfvars with lambda_image_uri
cd ../terraform
terraform apply
```

### 6. Test

Send a test email with a recipe image attached to `recipes@yourdomain.com`.

Check Lambda logs:
```bash
aws logs tail /aws/lambda/recipe-duck-processor-prod --follow
```

## Configuration Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `aws_region` | AWS region for deployment | `us-east-1` |
| `domain_name` | Your email domain | `example.com` |
| `email_whitelist` | Allowed sender emails (comma-separated) | `user@gmail.com,*@company.com` |
| `anthropic_api_key` | Anthropic API key | `sk-ant-...` |
| `notion_api_key` | Notion integration token | `ntn_...` |
| `notion_database_id` | Notion database ID | `abc123...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `environment` | `prod` | Environment name (used in resource names) |
| `project_name` | `recipe-duck` | Project name prefix for resources |
| `lambda_image_uri` | `""` | Lambda container image URI (set after building) |
| `anthropic_model` | `claude-3-5-sonnet-20241022` | Claude model to use |
| `lambda_timeout` | `300` | Lambda timeout in seconds |
| `lambda_memory` | `512` | Lambda memory in MB |
| `delete_emails_after_processing` | `true` | Delete emails from S3 after processing |

See [variables.tf](variables.tf) for complete list and descriptions.

## Infrastructure Components

### SES (Simple Email Service)

- **Domain verification** - Verifies domain ownership
- **Receipt rule set** - Defines email handling
- **Receipt rule** - Saves emails to S3 bucket

**Created resources:**
- `aws_ses_domain_identity.main`
- `aws_ses_receipt_rule_set.main`
- `aws_ses_receipt_rule.save_to_s3`

### S3 Bucket

Stores incoming emails temporarily before Lambda processing.

**Configuration:**
- Server-side encryption enabled
- Public access blocked
- Lifecycle policy (optional cleanup)
- SES write permissions
- Lambda read/delete permissions

**Created resources:**
- `aws_s3_bucket.email_bucket`
- `aws_s3_bucket_notification.lambda_trigger`

### Lambda Function

Processes recipe emails and pushes to Notion.

**Configuration:**
- Container image deployment (supports HEIC)
- 512 MB memory, 300s timeout
- CloudWatch Logs integration
- IAM role with minimal permissions
- Environment variables from Secrets Manager

**Created resources:**
- `aws_lambda_function.recipe_processor`
- `aws_iam_role.lambda_execution`
- `aws_cloudwatch_log_group.lambda_logs`
- `aws_lambda_permission.allow_s3`

### ECR Repository

Stores Lambda container images.

**Configuration:**
- Image scanning on push
- Lifecycle policy (keeps last 5 images)
- Tag immutability disabled (allows updates)

**Created resources:**
- `aws_ecr_repository.lambda_repository`

### Secrets Manager

Securely stores sensitive configuration.

**Secrets created:**
- `recipe-duck/prod/anthropic-api-key`
- `recipe-duck/prod/notion-api-key`
- `recipe-duck/prod/notion-database-id`
- `recipe-duck/prod/email-whitelist`

**Security:**
- Automatic rotation enabled (where supported)
- KMS encryption
- IAM-based access control

## Monitoring

### CloudWatch Logs

View Lambda execution logs:
```bash
# Follow logs in real-time
aws logs tail /aws/lambda/recipe-duck-processor-prod --follow

# View recent errors
aws logs tail /aws/lambda/recipe-duck-processor-prod --since 1h --filter-pattern ERROR
```

### CloudWatch Alarms

The infrastructure creates an alarm for Lambda errors:
- Triggers when >5 errors occur in 5 minutes
- Can be connected to SNS for notifications

### Metrics to Monitor

- **Lambda invocations** - Number of emails processed
- **Lambda errors** - Failed executions
- **Lambda duration** - Processing time
- **S3 bucket size** - Check for cleanup issues

## Cost Estimation

Approximate monthly costs (based on 100 recipes/month):

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Lambda | 100 invocations @ 30s avg | $0.00 (free tier) |
| S3 | Storage + requests | $0.10 |
| SES | 100 received emails | $0.00 (free tier) |
| CloudWatch Logs | 100 MB logs | $0.05 |
| Secrets Manager | 4 secrets | $1.60 |
| ECR | 1 GB storage | $0.10 |
| **Total** | | **~$1.85/month** |

Free tier assumptions:
- Lambda: 1M requests/month, 400,000 GB-seconds/month free
- SES: 1,000 received emails/month free (with EC2/Lambda)
- S3: 5 GB storage, 20,000 GET requests free

## Updating Infrastructure

### Update Variables

Edit `terraform.tfvars` and apply:
```bash
terraform apply
```

### Update Lambda Container Image

After pushing a new container image:
```bash
terraform apply
```

Terraform will detect the image update and deploy it.

### Add/Remove Whitelisted Emails

Option 1: Update terraform.tfvars and apply
```bash
# Edit terraform.tfvars
terraform apply
```

Option 2: Update secret directly
```bash
aws secretsmanager update-secret \
  --secret-id recipe-duck/prod/email-whitelist \
  --secret-string "new-list@example.com,another@example.com"
```

## Troubleshooting

### SES Domain Not Verified

1. Check DNS records are configured correctly
2. Wait up to 72 hours for verification
3. Verify with AWS CLI:
   ```bash
   aws ses get-identity-verification-attributes \
     --identities yourdomain.com \
     --region us-east-1
   ```

### Emails Not Arriving

1. **Check MX record** is configured correctly
2. **Verify sender** is in whitelist
3. **Check SES rule** is active:
   ```bash
   aws ses describe-active-receipt-rule-set --region us-east-1
   ```
4. **Test email sending** to verify DNS propagation

### Lambda Not Triggering

1. **Check S3 bucket** has events:
   ```bash
   aws s3api get-bucket-notification-configuration \
     --bucket $(terraform output -raw email_bucket_name)
   ```
2. **Verify Lambda permission** exists:
   ```bash
   terraform apply  # Recreates missing permission
   ```

### Permission Denied Errors

Lambda IAM role may be missing permissions:
```bash
terraform apply  # Recreates IAM policies
```

## Cleanup

To remove all infrastructure:

```bash
# 1. Delete Lambda container images first
aws ecr delete-repository \
  --repository-name recipe-duck-lambda \
  --force

# 2. Destroy infrastructure
terraform destroy
```

**Warning:** This deletes all resources including:
- S3 bucket and stored emails
- Secrets in Secrets Manager
- CloudWatch Logs
- ECR images

## Security Best Practices

1. **Use strong email whitelist** - Don't use `*@*` patterns
2. **Rotate API keys regularly** - Update secrets in Secrets Manager
3. **Monitor CloudWatch Logs** - Watch for unauthorized access attempts
4. **Enable CloudTrail** - Audit API calls (not included in this config)
5. **Use least privilege** - IAM roles have minimal required permissions
6. **Keep Terraform state secure** - Consider using S3 backend with encryption

## Remote State (Optional)

For team collaboration, store Terraform state in S3:

1. Create S3 bucket and DynamoDB table for state locking:
   ```bash
   aws s3 mb s3://my-terraform-state-bucket
   aws dynamodb create-table \
     --table-name terraform-state-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

2. Uncomment backend configuration in [main.tf](main.tf):
   ```hcl
   backend "s3" {
     bucket         = "my-terraform-state-bucket"
     key            = "recipe-duck/terraform.tfstate"
     region         = "us-east-1"
     encrypt        = true
     dynamodb_table = "terraform-state-lock"
   }
   ```

3. Migrate state:
   ```bash
   terraform init -migrate-state
   ```

## Support

For issues:
1. Check CloudWatch Logs for errors
2. Review [lambda/README.md](../lambda/README.md) for Lambda troubleshooting
3. Verify all prerequisites are met
4. Check AWS service quotas and limits
