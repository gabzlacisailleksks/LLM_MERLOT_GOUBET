# Lab 3 Security Fixes Summary

| Issue | File | Change Made | Status | Reference |
|-------|------|-------------|--------|-----------|
| Public S3 Bucket ACL | `terraform/main.tf` | Changed `acl` from `public-read` to `private` | Fixed | [AWS S3 ACLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html) |
| Open Security Group | `terraform/main.tf` | Restricted ingress from `0.0.0.0/0` to `10.0.0.0/8` | Fixed | [AWS Security Group Rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html) |
| Privileged Container | `k8s/deployment.yaml` | Set `privileged: false` and `allowPrivilegeEscalation: false` | Fixed | [K8s Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) |
| Container Running as Root | `k8s/deployment.yaml` | Enabled `runAsNonRoot: true` | Fixed | [K8s Configure Service Accounts](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/) |
| Floating Image Tag | `k8s/deployment.yaml` | Pinned image to `nginx:1.25` | Fixed | [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/) |
| Container Running as Root | `docker/Dockerfile` | Created `appuser` and switched to it using `USER appuser` | Fixed | [Docker User Instruction](https://docs.docker.com/engine/reference/builder/#user) |
| Unpinned Base Image | `docker/Dockerfile` | Pinned base image to `ubuntu:22.04` | Fixed | [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/) |
