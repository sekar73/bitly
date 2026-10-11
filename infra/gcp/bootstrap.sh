#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io curl openssl
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl --fail --location --retry 5 https://github.com/docker/compose/releases/download/v2.35.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
if [[ ! -f /swapfile ]]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi
swapon /swapfile || true
mkdir -p /opt/bitly
touch /opt/bitly/bootstrap-ready
