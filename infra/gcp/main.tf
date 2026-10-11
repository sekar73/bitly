terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
variable "project_id" { type = string }
variable "region" { default = "us-central1" }
variable "zone" { default = "us-central1-a" }
variable "machine_type" { default = "e2-micro" }
variable "allowed_cidr" {
  type = string
  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && var.allowed_cidr != "0.0.0.0/0"
    error_message = "Provide your public IPv4 /32; do not open the demo to everyone."
  }
}
resource "google_compute_network" "main" {
  name                    = "bitly-lab-network"
  auto_create_subnetworks = false
}
resource "google_compute_subnetwork" "main" {
  name          = "bitly-lab-subnet"
  ip_cidr_range = "10.42.1.0/24"
  region        = var.region
  network       = google_compute_network.main.id
}
resource "google_compute_firewall" "ingress" {
  name          = "bitly-lab-access"
  network       = google_compute_network.main.name
  source_ranges = [var.allowed_cidr]
  target_tags   = ["bitly-lab"]
  allow {
    protocol = "tcp"
    ports    = ["22", "80"]
  }
}
resource "google_compute_instance" "app" {
  name         = "bitly-lab"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["bitly-lab"]
  labels       = { project = "bitly-lab", environment = "learning", managed_by = "terraform" }
  boot_disk {
    auto_delete = true
    initialize_params {
      image  = "debian-cloud/debian-12"
      size   = 20
      type   = "pd-standard"
      labels = { project = "bitly-lab", environment = "learning", managed_by = "terraform" }
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.main.id
    access_config {}
  }
  metadata                  = { enable-oslogin = "TRUE", block-project-ssh-keys = "TRUE" }
  metadata_startup_script   = file("${path.module}/bootstrap.sh")
  allow_stopping_for_update = true
}
output "public_ip" { value = google_compute_instance.app.network_interface[0].access_config[0].nat_ip }
output "project_id" { value = var.project_id }
output "zone" { value = var.zone }
output "instance_name" { value = google_compute_instance.app.name }
