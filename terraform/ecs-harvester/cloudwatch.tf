# cloudwatch.tf

resource "random_id" "rand" {
  keepers = {
    # Generate a new id each time we switch to a new AMI id
    target_id = "${var.rand_id}"
  }
  byte_length = 4
}

resource "aws_cloudwatch_log_group" "harvester" {
  name = "${var.prefix}-${var.name}-${var.env}"
  retention_in_days = 7
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}

resource "aws_cloudwatch_event_target" "cw-target" {
  count     = var.az_count
  rule      = aws_cloudwatch_event_rule.cw_rule.name
  target_id = "${var.prefix}-${var.name}-${var.env}-every-day-${random_id.rand.dec}"
  # arn       = "${var.cluster_arn}"
  arn      = aws_ecs_cluster.harvester_cluster.arn
  role_arn = aws_iam_role.ecs_events.arn

  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.task.arn
    # needs network access
    network_configuration {
      subnets = var.subnets
      #subnets = ["${aws_subnet.public[count.index].id}"]
      security_groups  = ["${aws_security_group.public-group.id}"]
      assign_public_ip = true
    }
  }
  depends_on = [
    random_id.rand,
    aws_cloudwatch_event_rule.cw_rule,
    aws_ecs_task_definition.task,
    aws_iam_role.ecs_events,
    aws_ecs_cluster.harvester_cluster,
    aws_security_group.public-group
  ]
}


resource "aws_cloudwatch_event_rule" "cw_rule" {
  name                = "${var.prefix}-${var.name}-${var.env}-rule"
  schedule_expression = var.schedule_expression
  is_enabled          = true
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}
