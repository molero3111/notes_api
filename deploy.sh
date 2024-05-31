#!/bin/bash

if [ $(id -u) -ne 0 ]; then
  echo "Error: Script requires sudo privileges. Please run with 'sudo ./deploy.sh'."
  exit 1
fi


if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl command not found. Please install kubectl."
    exit 1
fi

#CREATING CONFIG MAP
configmap_name="notes-config"
echo "creating configmap: $configmap_name from .env file"
# Check if ConfigMap already exists
if kubectl get configmap $configmap_name &> /dev/null; then
  echo "ConfigMap $configmap_name already exists. Deleting..."
  kubectl delete configmap $configmap_name
fi
kubectl create configmap $configmap_name --from-env-file=.env
echo "created $configmap_name."

#CREATING SECRET
secret_name="notes-secret"
echo "creating secret: $secret_name from .env_secrets file"
# Check if ConfigMap already exists
if kubectl get secrets $secret_name &> /dev/null; then
  echo "Secret $secret_name already exists. Deleting..."
  kubectl delete secret $secret_name
fi
kubectl create secret generic $secret_name --from-env-file=.env.secrets
echo "created $secret_name"

# REDIS DEPLOYMENT
kubernetes_path="./kubernetes/redis"

if kubectl get deployment notes-redis-deployment  &> /dev/null; then
  echo "Redis deployment found. Restarting..."
  kubectl rollout restart deployment notes-redis-deployment
else
  echo "Redis deployment not found. Creating..."
  kubectl apply -f "$kubernetes_path"/deployment.yml
fi
echo "Creating redis service"
kubectl apply -f "$kubernetes_path"/service.yml

# POSTGRES DEPLOYMENT
kubernetes_path="./kubernetes/postgres"

# Persistent Volume
if kubectl get persistentvolume notes-postgres-pv  &> /dev/null; then
  echo "Postgres persistent volume found. No need to create it."
else
  echo "Postgres persistent volume not found. creating..."
  kubectl apply -f "$kubernetes_path"/postgres-pv.yml
fi

# Persistent Volume Claim
if kubectl get persistentvolumeclaim notes-postgres-pvc  &> /dev/null; then
  echo "Postgres persistent volume claim found. No need to create it."
else
  echo "Postgres persistent volume claim not found. creating..."
  kubectl apply -f "$kubernetes_path"/postgres-pvc.yml
fi

# Deployment
if kubectl get deployment notes-postgres-deployment  &> /dev/null; then
  echo "Postgres deployment found. Restarting..."
  kubectl rollout restart deployment notes-postgres-deployment
else
  echo "Postgres deployment not found. Creating..."
  kubectl apply -f "$kubernetes_path"/deployment.yml
fi

# Service
echo "Creating postgres service"
kubectl apply -f "$kubernetes_path"/service.yml

# API DEPLOYMENT
kubernetes_path="./kubernetes/api"

# Persistent Volume
if kubectl get persistentvolume notes-media-pv  &> /dev/null; then
  echo "API persistent volume found. No need to create it."
else
  echo "API persistent volume not found. creating..."
  kubectl apply -f "$kubernetes_path"/media-pv.yml
fi

# Persistent Volume Claim
if kubectl get persistentvolumeclaims notes-media-pvc  &> /dev/null; then
  echo "API persistent volume claim found. No need to create it."
else
  echo "API persistent volume claim not found. creating..."
  kubectl apply -f "$kubernetes_path"/media-pvc.yml
fi

# Deployment
if kubectl get deployment notes-app  &> /dev/null; then
  echo "API deployment found. Restarting..."
  kubectl rollout restart deployment notes-postgres-deployment
else
  echo "API deployment not found. Creating..."
  kubectl apply -f "$kubernetes_path"/deployment.yml
fi

# Service
echo "Creating API service"
kubectl apply -f "$kubernetes_path"/service.yml

# Service
echo "Creating API ingress"
kubectl apply -f "$kubernetes_path"/ingress.yml

echo "Deployment completed!"
