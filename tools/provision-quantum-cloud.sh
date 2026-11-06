#!/usr/bin/env bash
# Run in Google Cloud Shell. Preview by default.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash provision-quantum-cloud.sh PROJECT_ID ZONE BUCKET [--apply]

Use a dedicated project with billing enabled, or set BILLING_ACCOUNT to create
and link a new project or link an unbilled one. The bucket name must be globally
unique. Reruns reuse resources with the script's names in the selected project.
EOF
}

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
if [[ ${1:-} == --help ]]; then usage; exit 0; fi
[[ $# == 3 || ( $# == 4 && $4 == --apply ) ]] || { usage >&2; exit 2; }
project=$1 zone=$2 bucket=$3 mode=${4:-preview}
[[ $project =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || die "Invalid project ID"
[[ $zone =~ ^[a-z]+(-[a-z0-9]+)+[0-9]-[a-z]$ ]] || die "Invalid zone"
[[ $bucket =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] || die "Use a 3–63 character bucket name with lowercase letters, digits or hyphens"
region=${zone%-*}
network=quantum-vpc
subnet=quantum-subnet
router=quantum-router
nat=quantum-nat
vm=quantum-worker
service_name=quantum-runner
service_email="$service_name@$project.iam.gserviceaccount.com"

run() {
  if [[ $mode == --apply ]]; then
    "$@"
  else
    printf ' %q' "$@" >&2
    printf '\n' >&2
  fi
}

gc() { run gcloud --quiet --project="$project" "$@"; }

# An unsuccessful list is fatal. Only a successful list can establish absence.
ensure() {
  local name=$1 inventory=$2
  shift 2
  if [[ $mode == --apply ]] && grep -Fxq -- "$name" <<< "$inventory"; then
    printf 'Using existing %s\n' "$name" >&2
  else
    gc "$@" >&2
  fi
}

if [[ $mode == --apply ]]; then
  operator=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')
  [[ $operator =~ ^[^[:space:]@]+@[^[:space:]@]+$ && $operator != *.gserviceaccount.com ]] ||
    die "Select an active Google user account in Cloud Shell"
  projects=$(gcloud projects list --filter="projectId=$project" --format='value(projectId)')
  if ! grep -Fxq -- "$project" <<< "$projects"; then
    [[ -n ${BILLING_ACCOUNT:-} ]] || die "Select an existing project or set BILLING_ACCOUNT to create one"
    gcloud --quiet projects create "$project"
  fi
  billing=$(gcloud billing projects describe "$project" --format='value(billingEnabled)')
  if [[ ${billing,,} != true ]]; then
    [[ -n ${BILLING_ACCOUNT:-} ]] || die "Enable billing for $project or set BILLING_ACCOUNT"
    gcloud --quiet billing projects link "$project" --billing-account="$BILLING_ACCOUNT"
  fi
else
  operator='<active Cloud Shell user>'
  printf 'Project %s in %s. Apply uses its active billing account or BILLING_ACCOUNT.\n' "$project" "$zone" >&2
fi

gc services enable compute.googleapis.com storage.googleapis.com iam.googleapis.com \
  iap.googleapis.com oslogin.googleapis.com >&2

inventory() {
  if [[ $mode == --apply ]]; then gc "$@" --format='value(name)'; fi
}

names=$(inventory compute networks list)
ensure "$network" "$names" compute networks create "$network" --subnet-mode=custom
names=$(inventory compute networks subnets list --regions="$region")
ensure "$subnet" "$names" compute networks subnets create "$subnet" \
  --network="$network" --region="$region" --range=10.82.0.0/24 --enable-private-ip-google-access
names=$(inventory compute firewall-rules list)
ensure quantum-allow-iap "$names" compute firewall-rules create quantum-allow-iap \
  --network="$network" --direction=INGRESS --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 --target-tags=quantum-iap
names=$(inventory compute routers list --regions="$region")
ensure "$router" "$names" compute routers create "$router" --network="$network" --region="$region"
names=$(inventory compute routers nats list --router="$router" --region="$region")
ensure "$nat" "$names" compute routers nats create "$nat" --router="$router" \
  --region="$region" --nat-custom-subnet-ip-ranges="$subnet" --auto-allocate-nat-external-ips

if [[ $mode == --apply ]]; then
  names=$(gc iam service-accounts list --format='value(email)')
else
  names=''
fi
ensure "$service_email" "$names" iam service-accounts create "$service_name" --display-name="Quantum experiment VM"
names=$(inventory storage buckets list)
ensure "$bucket" "$names" storage buckets create "gs://$bucket" --location="$region" \
  --uniform-bucket-level-access --public-access-prevention
for role in roles/storage.objectViewer roles/storage.objectCreator; do
  gc storage buckets add-iam-policy-binding "gs://$bucket" \
    --member="serviceAccount:$service_email" --role="$role" >&2
done

# Scope SSH access to this VM and service-account use to this service account.
gc iam service-accounts add-iam-policy-binding "$service_email" \
  --member="user:$operator" --role=roles/iam.serviceAccountUser >&2
names=$(inventory compute instances list --zones="$zone")
ensure "$vm" "$names" compute instances create "$vm" --zone="$zone" \
  --subnet="$subnet" --no-address --tags=quantum-iap --metadata=enable-oslogin=TRUE \
  --machine-type=e2-highmem-2 --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced --service-account="$service_email" \
  --scopes=cloud-platform --max-run-duration=3600s --instance-termination-action=STOP
gc compute instances add-iam-policy-binding "$vm" --zone="$zone" \
  --member="user:$operator" --role=roles/compute.osLogin --condition=None >&2
gc projects add-iam-policy-binding "$project" --member="user:$operator" \
  --role=roles/iap.tunnelResourceAccessor \
  --condition='expression=destination.port == 22,title=Quantum SSH only' >&2

# Keep stdout machine-readable for copying to configs/cloud.local.json.
cat <<EOF
{
  "project": "$project",
  "region": "$region",
  "zone": "$zone",
  "vm": "$vm",
  "service_account": "$service_email",
  "bucket": "$bucket",
  "prefix": "quantum",
  "remote_root": "/var/tmp/quantum",
  "machine_type": "e2-highmem-2"
}
EOF
