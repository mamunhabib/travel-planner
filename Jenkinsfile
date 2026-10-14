pipeline {
    agent any

    triggers {
        // Poll GitHub every 2 minutes for automated CI/CD triggers on push
        pollSCM('H/2 * * * *')
    }

    environment {
        // Destination image path in GitHub Container Registry
        IMAGE_NAME = 'ghcr.io/mamunhabib/travel-planner'
        IMAGE_TAG  = "latest"
    }

    stages {
        stage('Build Docker Image') {
            steps {
                echo "Building the Docker Image via mounted Mac Docker daemon..."
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Push to GHCR') {
            steps {
                echo "Logging into GHCR and pushing image..."
                // Inject GitHub PAT credentials securely from Jenkins credential store
                withCredentials([usernamePassword(credentialsId: 'github-pat', passwordVariable: 'GITHUB_PAT', usernameVariable: 'GITHUB_USER')]) {
                    sh """
                    echo \$GITHUB_PAT | docker login ghcr.io -u \$GITHUB_USER --password-stdin
                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                    """
                }
            }
        }

        stage('Clean Local Image') {
            steps {
                echo "Removing image from Mac local Docker store to force Kubernetes to pull from GHCR..."
                sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo "Deploying declarative architecture to OrbStack Kubernetes..."
                // Applies all declarative manifests in k8s/ (namespaces, sealed secrets, configmap, deployments, services)
                sh "kubectl apply -f k8s/"

                echo "Restarting deployment to trigger fresh GHCR image pull..."
                sh "kubectl rollout restart deployment travel-planner -n travel-planner"
            }
        }
    }
}
