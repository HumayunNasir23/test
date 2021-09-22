pipeline {
    agent any
        environment {


    }
    stages {
        stage('test') {
            steps {
                script {

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
