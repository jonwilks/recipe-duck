"""AWS Lambda handler for processing recipe emails via SES."""

import json
import os
import email
import boto3
from email import policy
from email.parser import BytesParser
from typing import Optional, List, Dict, Any
import re
import sys
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Cache for secrets (Lambda container reuse)
_secrets_cache: Dict[str, str] = {}

# Match CLI default model unless explicitly overridden via environment.
DEFAULT_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-4-5')


def get_secret(secret_name: str) -> str:
    """Retrieve secret from AWS Secrets Manager with caching.

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Secret value as string
    """
    if secret_name in _secrets_cache:
        return _secrets_cache[secret_name]

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_value = response['SecretString']
        _secrets_cache[secret_name] = secret_value
        return secret_value
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
        raise


def is_email_whitelisted(sender_email: str, whitelist: str) -> bool:
    """Check if sender email is in whitelist.

    Args:
        sender_email: Email address of sender
        whitelist: Comma-separated list of allowed emails (supports wildcards)

    Returns:
        True if email is whitelisted, False otherwise
    """
    sender_email = sender_email.lower().strip()
    allowed_emails = [email.strip().lower() for email in whitelist.split(',')]

    for allowed in allowed_emails:
        if allowed == sender_email:
            return True
        # Support wildcard domain matching: *@example.com
        if allowed.startswith('*@'):
            domain = allowed[2:]
            if sender_email.endswith(f'@{domain}'):
                return True

    return False


def extract_sender_email(from_header: str) -> str:
    """Extract email address from From header.

    Args:
        from_header: Raw From header (e.g., "John Doe <john@example.com>")

    Returns:
        Email address only
    """
    match = re.search(r'<(.+?)>', from_header)
    if match:
        return match.group(1)
    return from_header


def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from email text.

    Args:
        text: Email body text

    Returns:
        List of URLs found in text
    """
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def parse_email_from_s3(bucket: str, key: str) -> email.message.Message:
    """Download and parse email from S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Parsed email message object
    """
    logger.info(f"Downloading email from s3://{bucket}/{key}")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    email_bytes = response['Body'].read()

    # Parse email
    msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
    return msg


def extract_attachments(msg: email.message.Message) -> List[Dict[str, Any]]:
    """Extract image attachments from email.

    Args:
        msg: Parsed email message

    Returns:
        List of attachment dicts with 'filename' and 'data' keys
    """
    attachments = []

    for part in msg.walk():
        # Look for image attachments
        if part.get_content_maintype() == 'image':
            filename = part.get_filename() or 'recipe_image.jpg'
            data = part.get_payload(decode=True)

            logger.info(f"Found image attachment: {filename} ({len(data)} bytes)")
            attachments.append({
                'filename': filename,
                'data': data,
                'content_type': part.get_content_type()
            })

    return attachments


def extract_email_body(msg: email.message.Message) -> str:
    """Extract plain text body from email.

    Args:
        msg: Parsed email message

    Returns:
        Email body as plain text
    """
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

    return body


def process_recipe_from_attachment(attachment: Dict[str, Any], api_key: str,
                                   notion_api_key: str, notion_db_id: str) -> str:
    """Process recipe from image attachment.

    Args:
        attachment: Attachment dict with 'data' and 'filename'
        api_key: Anthropic API key
        notion_api_key: Notion API key
        notion_db_id: Notion database ID

    Returns:
        Notion page URL
    """
    import tempfile
    from pathlib import Path

    # Import recipe-duck modules
    sys.path.insert(0, '/opt/python')  # Lambda layer path
    from recipe_duck.processor import RecipeProcessor
    from recipe_duck.notion_client import NotionRecipeClient

    # Determine file extension for temp file
    filename = attachment['filename'].lower()
    data = attachment['data']

    # Use original extension if available, preserve HEIC/HEIF
    if filename.endswith('.heic'):
        suffix = '.heic'
    elif filename.endswith('.heif'):
        suffix = '.heif'
    elif filename.endswith('.png'):
        suffix = '.png'
    else:
        suffix = '.jpg'

    logger.info(f"Processing image: {attachment['filename']} (format: {suffix})")

    # Write attachment to temporary file with correct extension
    # PIL with pillow-heif will handle HEIC natively
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_file.write(data)
        tmp_path = Path(tmp_file.name)

    try:
        # Process image with verbose logging for CloudWatch
        logger.info(f"Processing image: {attachment['filename']}")
        processor = RecipeProcessor(
            api_key=api_key,
            model=DEFAULT_MODEL,
            apply_formatting=True
        )
        markdown = processor.process_image(tmp_path, verbose=True)

        # Push to Notion with verbose logging
        logger.info("Pushing recipe to Notion")
        notion_client = NotionRecipeClient(
            api_key=notion_api_key,
            database_id=notion_db_id
        )
        page_url = notion_client.push_recipe(markdown, verbose=True)

        logger.info(f"Recipe created successfully: {page_url}")
        return page_url

    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


def process_recipe_from_url(url: str, api_key: str,
                            notion_api_key: str, notion_db_id: str) -> str:
    """Process recipe from URL.

    Args:
        url: Recipe URL
        api_key: Anthropic API key
        notion_api_key: Notion API key
        notion_db_id: Notion database ID

    Returns:
        Notion page URL
    """
    # Import recipe-duck modules
    sys.path.insert(0, '/opt/python')  # Lambda layer path
    from recipe_duck.processor import RecipeProcessor
    from recipe_duck.notion_client import NotionRecipeClient

    # Process URL with verbose logging for CloudWatch
    logger.info(f"Processing URL: {url}")
    processor = RecipeProcessor(
        api_key=api_key,
        model=DEFAULT_MODEL,
        apply_formatting=True
    )
    markdown = processor.process_url(url, verbose=True)

    # Push to Notion with verbose logging
    logger.info("Pushing recipe to Notion")
    notion_client = NotionRecipeClient(
        api_key=notion_api_key,
        database_id=notion_db_id
    )
    page_url = notion_client.push_recipe(markdown, verbose=True)

    logger.info(f"Recipe created successfully: {page_url}")
    return page_url


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for processing recipe emails.

    Args:
        event: S3 event from SES email receipt
        context: Lambda context object

    Returns:
        Response dict with status code and message
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract S3 bucket and key from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Get secrets
        anthropic_key = get_secret(os.environ['ANTHROPIC_API_KEY_SECRET'])
        notion_key = get_secret(os.environ['NOTION_API_KEY_SECRET'])
        notion_db = get_secret(os.environ['NOTION_DATABASE_ID_SECRET'])
        whitelist = get_secret(os.environ['EMAIL_WHITELIST_SECRET'])

        # Parse email from S3
        msg = parse_email_from_s3(bucket, key)

        # Extract sender and validate whitelist
        from_header = msg.get('From', '')
        sender_email = extract_sender_email(from_header)
        logger.info(f"Email from: {sender_email}")

        if not is_email_whitelisted(sender_email, whitelist):
            logger.warning(f"Email from {sender_email} not in whitelist. Rejecting.")
            return {
                'statusCode': 403,
                'body': json.dumps({'message': 'Sender not whitelisted'})
            }

        logger.info(f"Email from {sender_email} is whitelisted. Processing...")

        # Extract attachments and URLs
        attachments = extract_attachments(msg)
        body = extract_email_body(msg)
        urls = extract_urls_from_text(body)

        logger.info(f"Found {len(attachments)} image attachments and {len(urls)} URLs")

        results = []

        # Process image attachments
        for attachment in attachments:
            try:
                page_url = process_recipe_from_attachment(
                    attachment, anthropic_key, notion_key, notion_db
                )
                results.append({
                    'type': 'image',
                    'source': attachment['filename'],
                    'status': 'success',
                    'notion_url': page_url
                })
            except Exception as e:
                logger.error(f"Failed to process attachment {attachment['filename']}: {str(e)}")
                results.append({
                    'type': 'image',
                    'source': attachment['filename'],
                    'status': 'error',
                    'error': str(e)
                })

        # Process URLs
        for url in urls:
            try:
                page_url = process_recipe_from_url(
                    url, anthropic_key, notion_key, notion_db
                )
                results.append({
                    'type': 'url',
                    'source': url,
                    'status': 'success',
                    'notion_url': page_url
                })
            except Exception as e:
                logger.error(f"Failed to process URL {url}: {str(e)}")
                results.append({
                    'type': 'url',
                    'source': url,
                    'status': 'error',
                    'error': str(e)
                })

        # Cleanup: Delete email from S3
        if os.environ.get('DELETE_EMAILS_AFTER_PROCESSING', 'true').lower() == 'true':
            logger.info(f"Deleting email from S3: s3://{bucket}/{key}")
            s3_client.delete_object(Bucket=bucket, Key=key)

        # Return summary
        success_count = sum(1 for r in results if r['status'] == 'success')
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {success_count}/{len(results)} recipes successfully',
                'results': results
            })
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal error',
                'error': str(e)
            })
        }
