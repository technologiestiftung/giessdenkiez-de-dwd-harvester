variable "region" {
  description = "The region we are on"
}
variable "profile" {
  description = "The profile to use"
}
variable "name" {
  description = "a name for the bucket"
  default = "radolan-harvester"
}
variable "prefix" {
  description = "prefix for names"
  default     = "trees"
}

variable "env" {
  default = "dev"
}

variable "allowed_origins" {

  type = list(string)
}
