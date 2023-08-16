pipeline {
    agent any
    environment{
       VERSION = '1.1.0'
    } 
    stages {
        stage('Build') {
            steps {
                sh 'echo Build'
                sh 'ls'
                echo "Building version ${VERSION}"
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    def imageName = "python-program:${env.BUILD_NUMBER}"
                    
                    docker.build(imageName, '.')
                }
            }
        }
        stage('Test') {
            when {
                expression { env.BRANCH_NAME == 'develop'}
            }
            steps {
                sh 'echo Test'
                sh 'pwd'
            }
        }
        stage('Deploy') {
            steps {
                sh 'echo Deploy'
                sh 'touch newfile'
                script{
                   def environment = "staging"
                   if (environment == 'draas'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'aws-marketplace'){
                       echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'staging'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'ibm-pre-production'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'ibm-production'){
                       echo "Deploying on ${environment} instance"
                   }
                }
            }
        }
        stage('Deploy New') {
            steps {
                sh 'echo Deploy'
            }
        }
    }
    post{
        always{
         sh 'echo Always EXECUTION!!!'
        }
    }
}

