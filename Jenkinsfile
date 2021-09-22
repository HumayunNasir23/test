pipeline {
    agent any
        environment {
	FULL_PATH_BRANCH = "${sh(script:'git name-rev --name-only HEAD', returnStdout: true)}"
        BRANCH_NAME = FULL_PATH_BRANCH.substring(FULL_PATH_BRANCH.lastIndexOf('/') + 1, FULL_PATH_BRANCH.length())
    }
    stages {
        stage('test') {
            steps {
                script {
		    sh "echo ${env.BRANCH_NAME}"
		    echo env.BRANCH_NAME
                    if (env.BRANCH_NAME == 'thirsty') {
                        echo 'I only execute on the thirsty branch'
                    } 
		    else {
                        echo 'I execute elsewhere'
                    }
                }
            }
        }
    }
}
