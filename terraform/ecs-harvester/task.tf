resource "aws_cloudwatch_log_group" "harvester" {
  name = "${var.prefix}-${var.name}-${var.env}"
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees-harvester"
  }
}


resource "aws_ecs_task_definition" "task" {

  family                   = "${var.prefix}-${var.name}-${var.env}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution_role.arn
  # the difinition could also be located in a file
  # container_definitions = "${file("task-definitions/service.json")}"
  container_definitions = <<JSON
 [
  {
"logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "${aws_cloudwatch_log_group.harvester.name}",
                    "awslogs-region": "${var.region}",
                    "awslogs-stream-prefix": "${var.prefix}"
                }
            },

    "environment": [
      {"name":"ECS_AVAILABLE_LOGGING_DRIVERS",
      "value":"'[\"json-file\",\"awslogs\"]'"
      },
      {
        "name":"PG_SERVER",
        "value":"${var.pg_server}"
        },
      {
        "name":"PG_PORT",
        "value":"${var.pg_port}"
        },
      {
        "name":"PG_USER",
        "value":"${var.pg_user}"
        },
      {
        "name":"PG_PASS",
        "value":"${var.pg_pass}"
        },
      {
        "name":"PG_DB",
        "value":"${var.pg_db}"
        },
      {
        "name":"AWS_ACCESS_KEY_ID",
        "value":"${var.aws_access_key_id}"
        },
      {
        "name":"AWS_SECRET_ACCESS_KEY",
        "value":"${var.aws_secret_access_key}"
        },
      {
        "name":"S3_BUCKET",
        "value":"${var.s3_bucket}"
        },
      {
        "name":"OUTPUT",
        "value":"${var.output}"
        }
    ],
    "name": "${var.prefix}-${var.name}-${var.env}",
    "image": "${var.image}",
    "cpu": 256,
    "memory": 512,
    "essential": true,
    "portMappings": [
      {
        "containerPort": 5432,
        "hostPort": 5432
      }
    ]
  }
]
JSON
  tags = {
    name    = "${var.prefix}-${var.name}-${var.env}"
    project = "internet-of-trees"
  }
}
