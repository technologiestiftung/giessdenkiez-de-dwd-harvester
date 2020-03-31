# https://www.terraform.io/docs/providers/aws/r/db_instance.html
resource "aws_db_instance" "default" {
  allocated_storage      = "${var.pg_allocated_storage}"
  storage_type           = "${var.pg_storage_type}"
  engine                 = "${var.pg_engine}"
  engine_version         = "${var.pg_engine_version}"
  instance_class         = "${var.pg_instance_class}"
  name                   = "${var.pg_name}"
  username               = "${var.pg_user}"
  password               = "${var.pg_password}"
  parameter_group_name   = "${var.pg_parameter_group_name}"
  identifier             = "${var.pg_identifier}-${var.env_suffix}"
  publicly_accessible    = true
  apply_immediately      = true
  skip_final_snapshot    = true
  maintenance_window     = "Mon:00:00-Mon:03:00"
  backup_window          = "03:00-06:00"
  vpc_security_group_ids = ["${aws_security_group.rds.id}"]
  tags = {
    name    = "postgres db"
    project = "flusshygiene"
    type    = "db"
  }

  # https://www.terraform.io/docs/provisioners/local-exec.html
  provisioner "local-exec" {
    command = "psql -d ${var.pg_name} --host=${aws_db_instance.default.address} -U ${var.pg_user} -a -f ./provision/rds-install-postgis.sql"
    # command = "echo ${aws_db_instance.default.endpoint}"
    environment = {
      PGPASSWORD = "${var.pg_password}"
    }
  }
}

# -d flusshygiene --host=dev-flusshygiene.czirmde1gxcf.eu-central-1.rds.amazonaws.com -U wassergeist
