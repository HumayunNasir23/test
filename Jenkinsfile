pipeline {
    agent any
    stages {
        stage("foo") {
            steps {
                script {
                    def didTimeout = false
                    tags = sh(script: "git tag --sort=-v:refname", returnStdout: true).trim()
                    latest = sh(returnStdout:  true, script: "git tag --sort=-creatordate | head -n 1").trim()
                    try{
                    timeout(time: 20, unit: 'SECONDS') {
                    env.tag = input message: 'User input required', ok: 'Select!',
                            parameters: [choice(name: 'tag', choices: "${tags}", description: 'Select tag?')]
                    }
                    }catch(err) { // timeout reached or input false
                     def user = err.getCauses()[0].getUser()
                     if('SYSTEM' == user.toString()) { // SYSTEM means timeout.
                           didTimeout = true
                           env.tag = latest
                      } 
                      } 
                }
                      echo "${env.tag}"
            }
        }
    }
}
