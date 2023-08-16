pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'echo Build'
                sh 'ls'
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

