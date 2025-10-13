#!/bin/bash
# Build and push Lambda container image to AWS ECR
# This script builds a Docker image with HEIC support and pushes it to ECR

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_NAME="${ECR_REPOSITORY:-recipe-duck-lambda}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Recipe Duck Lambda Container Build & Push${NC}"
echo "=========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Docker: $(docker --version | cut -d' ' -f3)"
echo -e "${GREEN}[OK]${NC} AWS CLI: $(aws --version | cut -d' ' -f1 | cut -d'/' -f2)"
echo -e "${GREEN}[OK]${NC} AWS Account: $AWS_ACCOUNT_ID"
echo -e "${GREEN}[OK]${NC} AWS Region: $AWS_REGION"
echo ""

# ECR repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

# Check if ECR repository exists, create if not
echo "Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names "$REPOSITORY_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${YELLOW}Repository doesn't exist. Creating...${NC}"
    aws ecr create-repository \
        --repository-name "$REPOSITORY_NAME" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true \
        --output json > /dev/null
    echo -e "${GREEN}[OK]${NC} Created ECR repository: $REPOSITORY_NAME"
else
    echo -e "${GREEN}[OK]${NC} ECR repository exists: $REPOSITORY_NAME"
fi
echo ""

# Authenticate Docker to ECR
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo -e "${GREEN}[OK]${NC} Docker authenticated to ECR"
echo ""

# Build the Docker image
echo "Building Lambda container image..."
echo "This may take several minutes (compiling libheif from source)..."
echo ""

# Change to project root (parent of lambda directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

docker build \
    --no-cache \
    -f lambda/Dockerfile.lambda \
    -t "${REPOSITORY_NAME}:${IMAGE_TAG}" \
    -t "${ECR_URI}:${IMAGE_TAG}" \
    .

echo ""
echo -e "${GREEN}[OK]${NC} Container image built successfully"
echo ""

# Push to ECR
echo "Pushing image to ECR..."
docker push "${ECR_URI}:${IMAGE_TAG}"
echo -e "${GREEN}[OK]${NC} Image pushed to ECR"
echo ""

# Get image digest
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name "$REPOSITORY_NAME" \
    --image-ids imageTag="$IMAGE_TAG" \
    --region "$AWS_REGION" \
    --query 'imageDetails[0].imageDigest' \
    --output text)

echo "Deployment Details:"
echo "  Repository: $REPOSITORY_NAME"
echo "  Image URI: ${ECR_URI}:${IMAGE_TAG}"
echo "  Image Digest: $IMAGE_DIGEST"
echo "  Region: $AWS_REGION"
echo ""

echo -e "${GREEN}Build and push complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Update Terraform to use container image:"
echo "     - Set image_uri = \"${ECR_URI}:${IMAGE_TAG}\" in lambda.tf"
echo "  2. Run: cd terraform && terraform apply"
echo "  3. Test with an iPhone HEIC image"
echo ""
echo "To update the image later:"
echo "  ./build_and_push_container.sh"
