# Kubernetes Manifests for PDF Processing Pipeline

## Project Structure

```
cloud/
├── README.md                 # This file
├── namespace.yaml            # Namespace definition
├── service-account.yaml      # ServiceAccount with IRSA annotation
├── cronjob.yaml             # CronJob definition
├── iam-policy.json          # IAM policy for S3 access
└── trust-policy.json        # IAM trust policy for IRSA
```

## Setup Instructions

### 1. Prerequisites
- EKS cluster with OIDC provider enabled
- AWS CLI and kubectl configured
- eksctl or Terraform for IRSA setup

### 2. Create IAM Role (IRSA)

```bash
# Get your OIDC provider ID
aws eks describe-cluster --name <CLUSTER_NAME> --query "cluster.identity.oidc.issuer" --output text

# Replace placeholders in trust-policy.json
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGION="us-east-1"
export OIDC_ID="<YOUR_OIDC_ID>"

# Create IAM role
aws iam create-role \
  --role-name pdf-processor-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam put-role-policy \
  --role-name pdf-processor-role \
  --policy-name pdf-processor-s3-policy \
  --policy-document file://iam-policy.json
```

### 3. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create ServiceAccount
kubectl apply -f service-account.yaml

# Deploy CronJob
kubectl apply -f cronjob.yaml
```

### 4. Verify Deployment

```bash
# Check CronJob
kubectl get cronjob -n data-pipeline

# Check ServiceAccount
kubectl get sa pdf-processor-sa -n data-pipeline -o yaml

# Manual trigger for testing
kubectl create job --from=cronjob/pdf-processor-cronjob test-run-1 -n data-pipeline

# Check logs
kubectl logs -n data-pipeline -l app=pdf-processor
```

## Configuration

### Schedule
Current: `0 0 * * 0` (Every Sunday at midnight UTC)

Modify the `schedule` field in [cronjob.yaml](cronjob.yaml) to change frequency.

### Resources
- Requests: 1 CPU, 2Gi Memory
- Limits: 2 CPU, 4Gi Memory

Adjust based on your workload in [cronjob.yaml](cronjob.yaml).

### Output Format
Configured: `parquet` (recommended)

Set `OUTPUT_FORMAT=parquet` in [cronjob.yaml](cronjob.yaml).

## Security Features

1. **IRSA**: No AWS credentials in containers
2. **Non-root user**: Container runs as UID 1000
3. **Read-only filesystem**: Enhanced security posture with `/tmp` writable
4. **Resource limits**: Prevent resource exhaustion
5. **Least privilege IAM**: Only necessary S3 permissions

## Cost Optimization

1. **Spot Instances**: Node affinity configured for Spot
2. **TTL**: Jobs auto-cleanup after 1 hour
3. **Concurrency**: Forbid prevents resource waste
4. **Parquet**: 3-5x compression vs JSONL = lower storage costs

## Monitoring & Troubleshooting

```bash
# View recent job runs
kubectl get jobs -n data-pipeline

# Check failed pods
kubectl get pods -n data-pipeline --field-selector=status.phase=Failed

# Describe CronJob
kubectl describe cronjob pdf-processor-cronjob -n data-pipeline

# View pod logs
kubectl logs -n data-pipeline <POD_NAME>
```

## Error Handling

The pipeline implements a 3-tier S3 structure:
- `raw/`: Incoming PDFs
- `processed/`: Successfully processed data
- `error/`: Failed PDFs for manual review

Files that fail processing are moved to `error/` with metadata tags.
