resource "aws_ecs_cluster" "harvester_cluster" {
  name = "${var.prefix}-${var.name}-${var.env}"
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}
