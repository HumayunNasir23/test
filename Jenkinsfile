pipeline {
    environment {
    DRaaS_IP = '163.69.81.96'
    }
    agent any
    stages {
        stage ('Deploy') {
            steps{
                sshagent(credentials : ['jenkins-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} uptime"
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} \"touch newtestfile2\""

                }
            }
        }

    }
}
