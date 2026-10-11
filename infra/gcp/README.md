# Google Cloud deployment

The main [project README](../../README.md#deploy-to-google-cloud) contains the maintained GCP setup, deployment, testing, cost breakdown, budget alerts and cleanup instructions.

This directory contains the GCP Terraform configuration, VM bootstrap script and `.tfvars` example. Use `../../scripts/gcp-deploy.sh` and `../../scripts/gcp-destroy.sh` from the project root as `./scripts/gcp-deploy.sh` and `./scripts/gcp-destroy.sh`.

Keep `terraform.tfvars`, Terraform state, saved plans and credentials out of Git. Commit `.terraform.lock.hcl` to pin the provider version.
