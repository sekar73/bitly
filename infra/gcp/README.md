# Google Cloud deployment

The same Nginx gateway, separate Python read/write services, PostgreSQL and Redis run on one Compute Engine VM. Local and AWS configurations are retained. No Cloud SQL, Memorystore, GKE, load balancer or NAT gateway is created. Cloud data starts empty; this does not migrate your local/AWS database.

1. Create a dedicated Google Cloud project in the console and attach your billing account. Confirm trial eligibility and credit balance in Billing. Install Terraform and the Google Cloud CLI following https://cloud.google.com/sdk/docs/install.
2. Authenticate the CLI and Terraform separately:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable compute.googleapis.com --project=YOUR_PROJECT_ID
```

Your identity needs permission to provision networks/VMs/disks (Compute Admin or equivalent scoped permissions), enable APIs (Service Usage Admin), and log in with sudo via OS Login (Compute OS Admin Login). Grant roles in your project IAM to your own identity. Terraform uses Application Default Credentials; gcloud SSH uses your CLI identity. Do not download a service-account key for this workflow.

3. Set a budget before provisioning: Google Cloud Console → Billing → Budgets & alerts → Create budget. Select this project, choose $10/month (or your limit), and add actual spend thresholds at 50%, 90%, 100% and forecasted 100%. Ensure your account receives budget notifications. Alerts are delayed and are not a spending cap. The budget is configured in the console, not managed by this Terraform stack.
4. From the repository root:

```bash
cp infra/gcp/terraform.tfvars.example infra/gcp/terraform.tfvars
```

Set the project ID and your public IPv4 /32. Default region is us-central1, zone us-central1-a. Google regions use different names from AWS. e2-micro has 1 GiB memory; the five-container lab is tight but includes 1 GiB swap, as on AWS. Choose e2-small for 2 GiB if builds/runtime exhaust RAM, understanding that e2-small is not Free Tier eligible.

```bash
./scripts/gcp-deploy.sh
```

Review the plan, then type deploy. The script waits for bootstrap, uploads source without secrets, generates credentials on the VM, builds containers and checks both services. Re-running updates code without intentionally deleting data. Read every plan: VM/disk replacement erases data. No AWS resources are modified by this script.

5. Open the encrypted tunnel (leave it running):

```bash
gcloud compute ssh bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a -- -N -L 8080:localhost:80
```

Open http://localhost:8080. Register a cloud account and create a link. Change Postman base_url to this URL and run the collection. Automated tests:

```bash
TEST_BASE_URL=http://localhost:8080 ./scripts/test.sh
```

The tests retain cloud test accounts. The local service-isolation script is not for cloud deployment. Public HTTP is restricted to your IP but is unencrypted; use the tunnel for credentials/JWTs. PostgreSQL/Redis have no host ports. Desktop pgAdmin's local override is not uploaded.

Costs: eligible new users receive $300 trial credits for 90 days. Free Tier includes one e2-micro's eligible monthly hours in us-west1/us-central1/us-east1 and up to 30 GB standard persistent disk, subject to account limits shared across projects. Our 20 GB pd-standard disk and us-central1 defaults target those limits. Do not assume the entire stack is free: external IPv4 is listed at $0.005/hour (about $3.65 for 730 hours, unless your account receives a specific exemption), plus any excess transfer/storage/compute. Before Free Tier deductions, the published e2-micro rate in us-central1 is about $6.11/month. Confirm your account's actual eligibility and region rates in Billing; trial credits do not extend the trial deadline.

Official references:
- https://cloud.google.com/signup-faqs
- https://cloud.google.com/free/docs/free-cloud-features
- https://cloud.google.com/products/compute/pricing/general-purpose
- https://cloud.google.com/vpc/pricing

Tagging: VM and disk have project=bitly-lab, environment=learning, managed_by=terraform labels. Networking resources use bitly-lab-prefixed names; the firewall also targets the bitly-lab VM network tag. Use a separate Google project for this lab to isolate billing/resources. The VM has no attached service account; application containers do not need cloud API credentials.

Troubleshooting:

```bash
gcloud compute instances get-serial-port-output bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a
gcloud compute ssh bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a
# On the VM:
cd /opt/bitly
sudo docker compose ps
sudo docker compose logs --tail=100 gateway read write
sudo journalctl -u google-startup-scripts.service
```

If SSH is denied, check OS Login permissions, project ID and the source IP /32. If a deployment fails, resources can remain billable. Fix and rerun or destroy. Startup requires outbound internet for package/image downloads.

Cleanup:

```bash
./scripts/gcp-destroy.sh
```

This destroys only this GCP Terraform stack, including all cloud database data. It keeps the cloud project/billing connection/APIs/console budget, local data and AWS resources. Keep infra/gcp/terraform.tfstate until cleanup succeeds. AWS resources, if previously deployed, require ./scripts/aws-destroy.sh separately. Review both billing consoles; switching providers does not stop existing charges.

Validation: shell syntax and Terraform configuration are checked locally. A real cloud apply still requires your project, billing and credentials; it has not been run by the agent.
