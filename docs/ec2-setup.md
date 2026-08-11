# EC2 Environment Setup

This document records the exact state of the EC2 environment provisioned for the AI Knowledge Agent POC.

## EC2 Specifications
- **Instance ID**: `i-00ee324e6a85f1497`
- **Instance Type**: `t3.medium` (2 vCPU, 4 GiB RAM)
- **OS**: Ubuntu 24.04 LTS (Noble Numbat)
- **Disk**: 30 GB gp3 (`/dev/root`)
- **Network**: Public Subnet in `us-east-1a`
- **Access**: AWS Systems Manager (SSM) Session Manager

## Installed Software
- **Docker**: v29.1.3
- **Docker Compose**: v2.40.3
- **Git**: v2.43.0
- **Python**: v3.12.3

## Docker Configuration
The `ubuntu` user has been added to the `docker` group, allowing non-root execution of Docker commands.

## Accessing the Environment
To connect to the EC2 instance securely without SSH, run:
```bash
aws ssm start-session --target i-00ee324e6a85f1497
```

## Local Port Forwarding
To access internal application ports (e.g., React on 3000, FastAPI on 8000) from your local machine, use SSM port forwarding:
```bash
# Forward React port
aws ssm start-session --target i-00ee324e6a85f1497 --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["3000"],"localPortNumber":["3000"]}'

# Forward FastAPI port
aws ssm start-session --target i-00ee324e6a85f1497 --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}'
```
