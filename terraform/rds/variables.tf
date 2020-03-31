variable "region" {
  description = "The region to deploy the RDS instances in"
  default = "eu-central-1"
}

variable "profile" {}

variable "vpc_id" {}

variable "pg_user" {}
variable "pg_password" {}

variable "env_suffix" {
  default = "dev"
}

variable "pg_identifier" {
  default = "tf-trees"
}

variable "pg_allocated_storage" {
  default = 20
}

variable "pg_name" {
  default = "test"
}

variable "pg_engine_version" {
  default = "11.2"
}
variable "pg_engine" {
  default = "postgres"
}
variable "pg_instance_class" {
  default = "db.t2.micro"
}
variable "pg_parameter_group_name" {
  default = "default.postgres11"
}

variable "pg_storage_type" {
  default = "gp2"
}

