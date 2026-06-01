# Fetch an Ubuntu 22.04 LTS Machine Image automatically
data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

resource "aws_instance" "store_instance" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.Store_ai_instance_type
  key_name               = var.Store_ai_key_name
  vpc_security_group_ids = [aws_security_group.store_sg.id] # FIX: Attaches the SG to your instance

  # IMDSv2 enforced (security best practice — required by AWS Security Hub)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" 
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    encrypted             = true   # EBS encryption at rest
    delete_on_termination = true
  }

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io docker-compose-plugin git
    usermod -aG docker ubuntu
  EOF

  tags = {
    Name    = var.Store_ai_instance_name
    Project = var.Store_ai_project
  }
}

resource "aws_security_group" "store_sg" {
  name        = "store-ai-stack-sg"
  description = "Security group for ai stack"

  tags = {
    Name    = "store-stack-sg"
    Project = var.Store_ai_project
  }
}

# Web, API, and Application Ports (Kept open to your internet route variable)
locals {
  public_ports = [22, 80, 443, 3000, 3001, 8000, 8001]
}

resource "aws_vpc_security_group_ingress_rule" "public_ingress" {
  for_each          = toset([for p in local.public_ports : tostring(p)])
  security_group_id = aws_security_group.store_sg.id
  cidr_ipv4         = var.Store_ai_internet_route
  ip_protocol       = "tcp"
  from_port         = each.value
  to_port           = each.value
}

# Internal Infrastructure Ports (Restricted strictly to the local VPC / localhost loopback)
# WARNING: Exposing 6379, 9090, 9093 to the public internet creates severe vulnerabilities.
locals {
  internal_ports = [6379, 9090, 9093]
}

resource "aws_vpc_security_group_ingress_rule" "internal_ingress" {
  for_each          = toset([for p in local.internal_ports : tostring(p)])
  security_group_id = aws_security_group.store_sg.id
  cidr_ipv4         = "127.0.0.1/32" # Change this to your VPC CIDR (e.g., var.vpc_cidr) for multi-node setups
  ip_protocol       = "tcp"
  from_port         = each.value
  to_port           = each.value
}

resource "aws_vpc_security_group_egress_rule" "allow_all_outbound" {
  security_group_id = aws_security_group.store_sg.id
  cidr_ipv4         = "0.0.0.0/0" # FIX: Ensures instance can access the internet to install Docker packages
  ip_protocol       = "-1" 
}
