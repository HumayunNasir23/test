pipeline {
    agent any
    stages {
        stage('Example') {
            steps {
                echo "Running ${env.BUILD_ID} on ${env.JENKINS_URL}"
 
            }
        }
        stage ('Deploy') {
            steps{
                sshagent(credentials : ['jenkins-ssh']) {
                    sh 'ssh -o StrictHostKeyChecking=no root@163.69.83.205 uptime'
                    sh "ssh -o StrictHostKeyChecking=no root@163.69.83.205 \"touch newtestfile\""
                }
            }
        }

    }
}
