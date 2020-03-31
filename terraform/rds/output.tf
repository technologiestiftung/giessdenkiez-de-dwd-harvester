output "pg_host_address" {
  value = "${aws_db_instance.default.address}"
}

output "pg_user" {
  value = "${aws_db_instance.default.username}"
}
output "pg_aws_identifier" {
  value = "${aws_db_instance.default.identifier}"
}

output "pg_db_name" {
  value = "${aws_db_instance.default.name}"
}

output "pg_security_group_id" {
  value ="${aws_security_group.rds.id}"
}