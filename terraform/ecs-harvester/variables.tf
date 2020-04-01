variable "profile" {
  description = "The profile to work with. See your ~/.aws/credentials"
  default     = "default"
}

variable "region" {
  description = "The region to work in."
  default     = "eu-central-1"
}
variable "rand_id" {
  default = "123456"
}
variable "prefix" {
  description = "A name prefix added to all resources created"
  default     = "tf"
}

variable "name" {
  description = "The name of resources created"
  default     = "harvester"
}

variable "env" {
  description = "Just another suffix so you can have environments"
  default     = "dev"
}
variable "availability_zones" {
  description = "I Think there are only 3 in europe"
  default     = ["eu-central-1a", "eu-central-1b", "eu-central-1c"]
}
variable "az_count" {
  description = "Number of Availability Zones (AZs) to cover in a given region"
  default     = "2"
}
variable "vpc_id" {
  description = "The ID of your existing VPC where all the groups will be created in"
}
variable "subnets" {
  description = "List of subnets to create the container in"

}
variable "image" {
  description = "the image to use for your task"
  default     = "technologiestiftung/dwd-radolan-tree-harvester:test"
}


variable "schedule_expression" {
  description = "The schedule to run in. Could also be cron(*/5 * * * *) see https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html"
  # default     = "cron(0 8 * * ? *)"
  # every three minutes
  default = "cron(*/3 * * * ? *)"
}


# envs


variable "pg_server" {
  description = "an env variable for the container"
}
variable "pg_port" {
  description = "an env variable for the container"
  default     = 5432
}
variable "pg_user" {
  description = "an env variable for the container"
}
variable "pg_pass" {
  description = "an env variable for the container"
}
variable "pg_db" {
  description = "an env variable for the container"
}
variable "aws_access_key_id" {
  description = "an env variable for the container"
}
variable "aws_secret_access_key" {
  description = "an env variable for the container"
}
variable "s3_bucket" {
  description = "an env variable for the container"
}
variable "output" {
  description = "an env variable for the container"
}

