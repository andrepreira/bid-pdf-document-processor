#!/bin/bash
# Deployment script for PDF Processing Pipeline on EKS

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== PDF Processor EKS Deployment ===${NC}\n"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}kubectl not found${NC}"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo -e "${RED}aws CLI not found${NC}"; exit 1; }

# Get AWS account and cluster info
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGION=${AWS_REGION:-us-east-1}
export CLUSTER_NAME=${EKS_CLUSTER_NAME:-my-eks-cluster}

echo -e "${GREEN}✓ AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}✓ Region: ${REGION}${NC}"
echo -e "${GREEN}✓ Cluster: ${CLUSTER_NAME}${NC}\n"

# Get OIDC ID
echo -e "${YELLOW}Retrieving OIDC provider...${NC}"
OIDC_URL=$(aws eks describe-cluster --name ${CLUSTER_NAME} --query "cluster.identity.oidc.issuer" --output text)
OIDC_ID=$(echo ${OIDC_URL} | cut -d '/' -f 5)
echo -e "${GREEN}✓ OIDC ID: ${OIDC_ID}${NC}\n"

# Create IAM role
echo -e "${YELLOW}Creating IAM role...${NC}"
cat trust-policy.json | \
  sed "s/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g" | \
  sed "s/<REGION>/${REGION}/g" | \
  sed "s/<OIDC_ID>/${OIDC_ID}/g" > trust-policy-rendered.json

aws iam create-role \
  --role-name pdf-processor-role \
  --assume-role-policy-document file://trust-policy-rendered.json \
  2>/dev/null || echo -e "${YELLOW}Role already exists, continuing...${NC}"

aws iam put-role-policy \
  --role-name pdf-processor-role \
  --policy-name pdf-processor-s3-policy \
  --policy-document file://iam-policy.json

echo -e "${GREEN}✓ IAM role created/updated${NC}\n"

# Deploy Kubernetes resources
echo -e "${YELLOW}Deploying Kubernetes resources...${NC}"

kubectl apply -f namespace.yaml
echo -e "${GREEN}✓ Namespace created${NC}"

# Update ServiceAccount with correct IAM role ARN
cat service-account.yaml | \
  sed "s/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g" | \
  kubectl apply -f -
echo -e "${GREEN}✓ ServiceAccount created${NC}"

# Update CronJob with correct ECR image
cat cronjob.yaml | \
  sed "s/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g" | \
  sed "s/<REGION>/${REGION}/g" | \
  kubectl apply -f -
echo -e "${GREEN}✓ CronJob created${NC}"

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Build and push Docker image to ECR"
echo "2. Verify CronJob: kubectl get cronjob -n data-pipeline"
echo "3. Test manually: kubectl create job --from=cronjob/pdf-processor-cronjob test-1 -n data-pipeline"
echo "4. Monitor logs: kubectl logs -n data-pipeline -l app=pdf-processor -f"
