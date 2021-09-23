pipeline {
    agent any
     environment {
	     BRANCH_NAME = "${GIT_BRANCH.split("/")[1]}"
     }
    stages {
        stage('test') {
            steps {
                script {

		    echo env.BRANCH_NAME
		    echo env.deployed
		    env.deployed = 'true'
		    echo env.deployed
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
