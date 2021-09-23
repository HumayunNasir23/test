pipeline {
    agent any
    stages {
        stage("foo") {
            steps {
                script {
                    env.tag = input message: 'User input required', ok: 'Release!',
                            parameters: [choice(name: 'tag', choices: '1.0\n2.0\n3.0', description: 'Select tag?')]
                }
                echo "${env.tag}"
            }
        }
    }
}
