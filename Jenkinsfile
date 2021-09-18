pipeline {
    environment {
    DRaaS_IP = '163.69.81.96'
    }
    agent any
    stages {
        stage ('Deploy backend') {
            steps{
                sshagent(credentials : ['jenkins-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} uptime"
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} \"kubectl apply -f dep.yaml\""

                }
            }
        }
        stage ('Deploy frontend') {
            steps{
                sshagent(credentials : ['jenkins-ssh']) {
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} uptime"
                    sh "ssh -o StrictHostKeyChecking=no root@${env.DRaaS_IP} \"kubectl apply -f folder/dep.yaml\""

                }
            }
        }

    }
}
