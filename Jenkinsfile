pipeline {
    agent any
    stages {
        stage("foo") {
            steps {
                script {
                    tags = sh(script: "git describe --tags", returnStdout: true).trim()
                    env.tag = input message: 'User input required', ok: 'Select!',
                            parameters: [choice(name: 'tag', choices: "${tags}", description: 'Select tag?')]
                }
                echo "${env.tag}"
            }
        }
    }
}
