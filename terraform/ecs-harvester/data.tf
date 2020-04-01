# data.tf

# Fetch AZs in the current region
data "aws_availability_zones" "available" {
}

# data "aws_vpc" "default" {
#   id = "${var.vpc_id}"
# }
