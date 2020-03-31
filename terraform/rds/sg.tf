resource "aws_security_group" "rds" {
  name        = "terraform_rds_sg-${var.pg_identifier}-${var.env_suffix}"
  description = "flusshygiene RDS"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    # this is okay for our development setup
    # in production the EB only should have access to the SG
    # can be done using its securoty group
  }
  # Allow all outbound traffic.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    name    = "terraform-rds-security-group"
    project = "${var.pg_identifier}"
    type    = "rds security group"
  }
}
