pipeline {
    agent any
    stages {
        stage('Example') {
            steps {
                echo "Running ${env.BUILD_ID} on ${env.JENKINS_URL}"
 
            }
        }
        stage('SSH into the server') {
            steps {
                script {
                    def remote = [:]
                    remote.name = 'hu-jenkins-testing-do-not-delete'
                    remote.host = '163.69.83.205'
                    remote.user = 'root'
                    remote.password = ''
                    remote.allowAnyHosts = true
                    sshCommand remote: remote, command: "sudo ls"

                }
            }
        }
    }
}
