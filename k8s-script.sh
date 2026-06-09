#!/bin/bash
set -e

echo "================================================"
echo "Deploying Project Gutenberg Backend to Kind Cluster"
echo "================================================"

read -n 1 -p "Before starting, make sure you have installed kubeseal and docker (should be launched). Press enter to continue..."

read -n 1 -p "Do you want to create a new Kind Cluster? (y/n): " create_cluster
if [ "$create_cluster" == "y" ]; then
    echo -e "\n\nCreating Kind Cluster..."
    kind create cluster --config deployment/kind-config.yaml
    echo "Done"

    echo -e "\n\nCreating Sealed Secrets Controller..."
    kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.1/controller.yaml
    echo "Waiting for Sealed Secrets controller to be ready..."
    kubectl wait --for=condition=available --timeout=120s deployment/sealed-secrets-controller -n kube-system
    echo "Done"

    echo -e "\n\nEncrypting Secrets..."
    kubeseal --fetch-cert --controller-name=sealed-secrets-controller --controller-namespace=kube-system > deployment/env-config/public-cert.pem
    kubeseal --cert=deployment/env-config/public-cert.pem --format=yaml < deployment/env-config/secrets.yml > deployment/env-config/sealedsecret.yaml
    echo "Done"

    echo -e "\n\nCreating Docker Image..."
    docker build -t localhost:5000/gutenberg-backend:local .
    docker push localhost:5000/gutenberg-backend:local
    kind load docker-image localhost:5000/gutenberg-backend:local --name gutenberg-kind-cluster
    echo "Done"
else
    echo -e "\n\nLoading Docker Image..."
    docker build -t localhost:5000/gutenberg-backend:local .
    kind load docker-image localhost:5000/gutenberg-backend:local --name gutenberg-kind-cluster
    kubectl rollout restart deployment/gutenberg-backend
    kubectl rollout status deployment/gutenberg-backend --timeout=120s
    echo "Done"
fi

echo -e "\n\nCreating ConfigMaps and Secrets..."
kubectl apply -f deployment/env-config/configmap.yaml
kubectl apply -f deployment/env-config/sealedsecret.yaml
echo "Done"

echo -e "\n\nCreating Postgres..."
kubectl apply -f deployment/db-config/postgres-storage.yaml
kubectl apply -f deployment/db-config/postgres.yaml
echo -e "\n\nWaiting for Postgres to be ready..."
kubectl wait --for=condition=ready pod/gutenberg-postgres-0 --timeout=120s
echo "Done"

echo -e "\n\nCreating Redis..."
kubectl apply -f deployment/db-config/redis-storage.yaml
kubectl apply -f deployment/db-config/redis.yaml
echo -e "\n\nWaiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/gutenberg-redis
echo "Done"

echo -e "\n\nRunning Database Migrations..."
kubectl delete job gutenberg-migrate --ignore-not-found
kubectl apply -f deployment/backend-config/migrate-job.yaml
kubectl wait --for=condition=complete job/gutenberg-migrate --timeout=120s
echo "Done"

echo -e "\n\nCreating Backend Deployment..."
kubectl apply -f deployment/backend-config/backend.yaml
echo -e "\n\nWaiting for Backend to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/gutenberg-backend
echo "Done"

echo -e "\n\n================================================"
echo "Project Gutenberg Backend deployed to Kind Cluster"
echo "================================================"
echo -e "\n"