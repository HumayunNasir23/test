pipeline {
    agent any

    stages {
        stage('test') {
            steps {
                sh 'echo hello'
            }
        }
        stage('test1') {
            steps {
                sh 'echo $TEST'
            }
        }
        stage('test3') {
            steps {
                script {
                    if (env.BRANCH_NAME == 'thirsty') {
                        echo 'I only execute on the thirsty branch'
                    } else {
                        echo 'I execute elsewhere'
                    }
                }
            }
        }
    }
}
