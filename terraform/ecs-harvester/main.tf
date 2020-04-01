provider "aws" {
  profile = var.profile
  region  = var.region
  version = "~> 2.55"
}

provider "random" {
  version = "~> 2.2"
}
