# ECR repository for Lambda container images
resource "aws_ecr_repository" "lambda_container" {
  name                 = "${var.project_name}-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-lambda-ecr"
  }
}

# Lifecycle policy to keep only recent images
resource "aws_ecr_lifecycle_policy" "lambda_container" {
  repository = aws_ecr_repository.lambda_container.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Output ECR repository URI
output "ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  value       = aws_ecr_repository.lambda_container.repository_url
}
