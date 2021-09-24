pipeline {
    agent any
    stages {
        stage("foo") {
            steps {
                script {
                    tags = sh(script: "git tag --sort=-v:refname", returnStdout: true).trim()
                    latest = sh(returnStdout:  true, script: "git tag --sort=-creatordate | head -n 1").trim()
                    long startTime = System.currentTimeMillis()
                    try{
                    timeout(time: 20, unit: 'SECONDS') {
                    env.tag = input message: 'User input required', ok: 'Select!',
                            parameters: [choice(name: 'tag', choices: "${tags}", description: 'Select tag?')]
                    }
                    }catch (err) {
                       long timePassed = System.currentTimeMillis() - startTime
                       if (timePassed >= timeoutInSeconds * 1000) {
                           echo 'Timed out'
                           env.tag = latest
                       } else {
                       throw err
                    }
                    }

                   }
                      echo "${env.tag}"
            }
        }
    }
}
