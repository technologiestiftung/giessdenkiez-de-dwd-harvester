provider "aws" {
  profile = var.profile
  region  = var.region
  version = "~> 3.0"
}

provider "random" {
  version = "~> 2.2"
}
