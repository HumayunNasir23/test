pipeline {
  agent any
  environment {
    FULL_PATH_BRANCH = "${sh(script:'git name-rev --name-only HEAD', returnStdout: true)}"
    GIT_BRANCH = FULL_PATH_BRANCH.substring(FULL_PATH_BRANCH.lastIndexOf('/') + 1, FULL_PATH_BRANCH.length())
  }
   stages {
        stage('Build') {
            steps {
              sh "echo ${env.GIT_BRANCH}"
              if(env.GIT_BRANCH=='thirsty'){
                echo 'thirsty branch is current'
                
              }
              else if(env.GIT_BRANCH=='main'){
                echo 'main branch is current'
                
              }
            }
        }
    }
  
}
