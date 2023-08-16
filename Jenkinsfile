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

