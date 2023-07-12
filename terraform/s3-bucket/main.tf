provider "aws" {
  profile = var.profile
  region  = var.region
  version = "~> 3.0"
}

output "s3-bucket-name-radolan" {
  value = "${aws_s3_bucket.radolan.bucket_domain_name}"
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = "${var.prefix}-${var.name}-${var.env}"
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket" "radolan" {
  bucket        = "${var.prefix}-${var.name}-${var.env}"
  force_destroy = true
  versioning {
    enabled = false
  }

  policy = jsonencode({
    "Version" = "2012-10-17"
    "Id"      = "Policy-public-read-1"
    "Statement" = [
      {
        "Sid"       = "AllowPublicRead"
        "Effect"    = "Allow"
        "Principal" = "*"
        "Action"    = "s3:GetObject"
        "Resource"  = "arn:aws:s3:::${var.prefix}-${var.name}-${var.env}/*"
      }
    ]
  })

  # Should be added for production
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 6000
  }

  tags = {
    name    = "terraform bucket for uploads from radolan recent module"
    project = "flsshygn"
    type    = "storage"
  }

}
