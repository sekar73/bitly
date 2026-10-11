terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, Environment = "learning", ManagedBy = "Terraform" }
  }
}
variable "region" { default = "us-east-1" }
variable "project" {
  default = "bitly-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "Use a lowercase project slug of 3–25 characters."
  }
}
variable "allowed_cidr" {
  type        = string
  description = "Your public IP /32. Only this range can reach HTTP or SSH."
  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && var.allowed_cidr != "0.0.0.0/0"
    error_message = "Provide a restricted CIDR; do not expose this learning app to the entire internet."
  }
}
variable "ssh_public_key" { type = string }
variable "budget_email" { type = string }
variable "budget_usd" { default = 15 }
variable "instance_type" { default = "t3.micro" }

data "aws_ami" "linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project}-vpc" }
}
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.42.1.0/24"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-public" }
}
resource "aws_internet_gateway" "main" { vpc_id = aws_vpc.main.id }
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_security_group" "app" {
  name   = "${var.project}-app"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_key_pair" "app" {
  key_name   = "${var.project}-key"
  public_key = var.ssh_public_key
}
resource "aws_instance" "app" {
  ami                         = data.aws_ami.linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  key_name                    = aws_key_pair.app.key_name
  user_data                   = file("${path.module}/bootstrap.sh")
  user_data_replace_on_change = true
  metadata_options { http_tokens = "required" }
  credit_specification { cpu_credits = "standard" }
  root_block_device {
    volume_size           = 10
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
    tags                  = { Project = var.project, Environment = "learning", ManagedBy = "Terraform" }
  }
  tags       = { Name = "${var.project}-app" }
  depends_on = [aws_route_table_association.public]
}
resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-account-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  # Account-wide to include IPv4, storage and other costs even before tag activation.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}
output "public_ip" { value = aws_instance.app.public_ip }
output "instance_id" { value = aws_instance.app.id }
output "url" { value = "http://${aws_instance.app.public_ip}" }
