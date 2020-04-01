resource "aws_iam_role" "task_execution_role" {
  name               = "${var.prefix}-${var.name}-${var.env}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "ec2.amazonaws.com",
          "ecs-tasks.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

  description = "terraform ${var.name} role for executing containers"
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}


resource "aws_iam_role_policy_attachment" "ecs-task-execution-role-policy" {
  role       = aws_iam_role.task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

}
resource "aws_security_group" "public-group" {
  name        = "${var.prefix}-${var.name}-${var.env}"
  description = "controls access to the ${var.prefix}-${var.name}-${var.env}"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    self        = true
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    self        = true
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    self        = true
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    self        = true
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ingress {
  #   from_port   = 22
  #   to_port     = 22
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  # }
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
  egress {
    self        = true
    from_port   = 0
    to_port     = 0
    protocol    = -1
    cidr_blocks = ["0.0.0.0/0"]
  }
}


resource "aws_iam_role" "ecs_events" {
  name = "${var.prefix}-${var.name}-${var.env}-events"

  assume_role_policy = <<DOC
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
DOC
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}

resource "aws_iam_role_policy" "ecs_events_run_task_with_any_role" {
  name = "${var.prefix}-${var.name}-${var.env}-run-task-with-any-role"
  role = aws_iam_role.ecs_events.id

  policy = <<DOC
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "ecs:RunTask",
            "Resource": "${replace(aws_ecs_task_definition.task.arn, "/:\\d+$/", ":*")}"
        }
    ]
}
DOC

}
