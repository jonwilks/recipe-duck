# Lambda Function

This directory contains the AWS Lambda function for processing recipe emails.

## Architecture

**Email Flow:**
```
Email -> SES -> S3 -> Lambda -> RecipeProcessor -> Notion
```

The Lambda function:
1. Receives S3 event notifications when emails arrive
2. Parses email content and extracts attachments
3. Validates sender against whitelist
4. Processes recipe images/URLs using Claude AI
5. Pushes results to Notion database
6. Cleans up processed emails from S3

## Files

- **`lambda_handler.py`** - Main Lambda entry point
- **`Dockerfile.lambda`** - Container image definition with HEIC support
- **`requirements.txt`** - Python dependencies
- **`build_and_push_container.sh`** - Build and deploy script
- **`.gitignore`** - Excludes build artifacts

## Prerequisites

- Docker installed and running
- AWS CLI installed and configured
- AWS account with appropriate permissions
- Terraform infrastructure deployed (creates ECR repository)

## Building and Deploying

### Step 1: Build and Push Container Image

The Lambda function runs as a container image with full HEIC support for iPhone photos:

```bash
./build_and_push_container.sh
```

This script will:
1. Check prerequisites (Docker, AWS CLI)
2. Create ECR repository if needed
3. Build container image with libheif libraries
4. Push image to AWS ECR
5. Display deployment details

**Environment variables (optional):**
```bash
export AWS_REGION=us-east-1           # AWS region (default: us-east-1)
export ECR_REPOSITORY=recipe-duck-lambda  # ECR repo name (default: recipe-duck-lambda)
export IMAGE_TAG=latest               # Image tag (default: latest)
```

### Step 2: Update Terraform

After building the container image, update Terraform to use it:

```bash
cd ../terraform

# Add to terraform.tfvars:
# lambda_image_uri = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/recipe-duck-lambda:latest"

terraform apply
```

The image URI will be displayed by the build script.

## Environment Variables

The Lambda function expects these environment variables (automatically configured by Terraform):

- `ANTHROPIC_API_KEY_SECRET` - AWS Secrets Manager secret name for Anthropic API key
- `NOTION_API_KEY_SECRET` - AWS Secrets Manager secret name for Notion API key
- `NOTION_DATABASE_ID_SECRET` - AWS Secrets Manager secret name for Notion database ID
- `EMAIL_WHITELIST_SECRET` - AWS Secrets Manager secret name for email whitelist
- `ANTHROPIC_MODEL` - Claude model to use (default: claude-3-5-sonnet-20241022)
- `DELETE_EMAILS_AFTER_PROCESSING` - Whether to delete emails from S3 after processing (default: true)

## Local Testing

Test the container image locally before deploying:

```bash
# Build image
docker build -f Dockerfile.lambda -t recipe-duck-lambda .

# Run locally (requires AWS credentials and secrets)
docker run -p 9000:8080 \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_REGION=us-east-1 \
  -e ANTHROPIC_API_KEY_SECRET=your-secret-name \
  -e NOTION_API_KEY_SECRET=your-secret-name \
  -e NOTION_DATABASE_ID_SECRET=your-secret-name \
  -e EMAIL_WHITELIST_SECRET=your-secret-name \
  -e ANTHROPIC_MODEL=claude-3-5-sonnet-20241022 \
  -e DELETE_EMAILS_AFTER_PROCESSING=true \
  recipe-duck-lambda

# In another terminal, invoke with test event
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{
  "Records": [{
    "s3": {
      "bucket": {"name": "your-bucket"},
      "object": {"key": "emails/test-email"}
    }
  }]
}'
```

## Monitoring

### CloudWatch Logs

View Lambda execution logs:

```bash
# Real-time logs
aws logs tail /aws/lambda/recipe-duck-processor-prod --follow

# Recent logs
aws logs tail /aws/lambda/recipe-duck-processor-prod --since 1h

# Search for errors
aws logs filter-pattern /aws/lambda/recipe-duck-processor-prod --filter-pattern "ERROR"
```

### Lambda Metrics

View in AWS Console: Lambda -> recipe-duck-processor-prod -> Monitor tab

Key metrics to watch:
- **Invocations** - Number of times function was triggered
- **Errors** - Failed executions
- **Duration** - Execution time per invocation
- **Throttles** - Concurrent execution limit reached

## Troubleshooting

### Email Not Processed

1. **Check CloudWatch Logs** for errors:
   ```bash
   aws logs tail /aws/lambda/recipe-duck-processor-prod --follow
   ```

2. **Verify sender is whitelisted**:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id recipe-duck/prod/email-whitelist \
     --query SecretString --output text
   ```

3. **Check SES receipt rule is active**:
   ```bash
   aws ses describe-active-receipt-rule-set --region us-east-1
   ```

4. **Verify email was saved to S3**:
   ```bash
   aws s3 ls s3://recipe-duck-emails-prod-ACCOUNT_ID/emails/
   ```

### Lambda Timeout

- Default timeout is 300 seconds (5 minutes)
- Increase in `terraform/variables.tf` if needed
- Check for large image attachments
- Monitor duration in CloudWatch metrics

### Out of Memory

- Default memory is 512 MB
- Increase in `terraform/variables.tf` if needed
- Monitor memory usage in CloudWatch logs

### Secrets Not Found

1. **Verify secrets exist**:
   ```bash
   aws secretsmanager list-secrets
   ```

2. **Check Lambda has IAM permissions** to read secrets (configured by Terraform)

3. **Verify environment variables** point to correct secret names:
   ```bash
   aws lambda get-function-configuration \
     --function-name recipe-duck-processor-prod \
     --query 'Environment.Variables'
   ```

### HEIC/HEIF Images (iPhone Photos)

Container deployment includes full HEIC support via:
- Native libheif and libde265 libraries
- pillow-heif Python package
- Automatic format detection and conversion

If HEIC images fail:
1. Check CloudWatch logs for specific error
2. Verify image was properly attached (not inline)
3. Test with JPEG image to isolate HEIC-specific issues

## Email Whitelist Format

The email whitelist is stored in AWS Secrets Manager as a comma-separated string:

```
user1@example.com,user2@example.com,*@yourdomain.com
```

**Supported patterns:**
- Individual emails: `alice@gmail.com`
- Wildcard domains: `*@company.com`
- Mixed: `alice@gmail.com,*@company.com,bob@yahoo.com`

Email matching is case-insensitive.

**Update whitelist:**
```bash
aws secretsmanager update-secret \
  --secret-id recipe-duck/prod/email-whitelist \
  --secret-string "user1@example.com,user2@example.com"
```

## Updating the Function

To deploy code changes:

```bash
# 1. Build and push new image
./build_and_push_container.sh

# 2. Update Lambda to use new image
aws lambda update-function-code \
  --function-name recipe-duck-processor-prod \
  --image-uri ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/recipe-duck-lambda:latest
```

Or use Terraform:
```bash
cd terraform
terraform apply
```

Lambda will automatically pull the latest image version on next invocation.

## Container Image Details

The Dockerfile builds a Lambda-compatible container with:

**Base Image:** `public.ecr.aws/lambda/python:3.11`

**System Dependencies:**
- libheif and libde265 for HEIC support
- Image processing tools (libffi, libjpeg, etc.)

**Python Dependencies:**
- anthropic - Claude AI SDK
- notion-client - Notion API client
- pillow-heif - HEIC image support
- beautifulsoup4 - HTML parsing for URL extraction
- All dependencies from `requirements.txt`

**Build Process:**
1. Install system dependencies
2. Download and compile libheif from source
3. Install Python dependencies
4. Copy lambda_handler.py and source code
5. Set Lambda handler entrypoint
