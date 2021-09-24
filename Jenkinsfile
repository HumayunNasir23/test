pipeline {
    agent any
    stages {
        stage("foo") {
            steps {
                script {
                    tags = sh(script: "git tag --sort=-v:refname", returnStdout: true).trim()
                    latest = sh(returnStdout:  true, script: "git tag --sort=-creatordate | head -n 1").trim()
                    timeout(time: 20, unit: 'SECONDS') {
                    env.tag = input message: 'User input required', ok: 'Select!',
                            parameters: [choice(name: 'tag', choices: "${tags}",defaultValue: latest, description: 'Select tag?')]
                    }
                }
                echo "${env.tag}"
            }
        }
    }
}
