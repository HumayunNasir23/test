pipeline {
    agent any
    stages {
        stage("Testing") {
            steps {
                script {
                    long startTime = System.currentTimeMillis()
                    timeoutInSeconds =20
                    try{
                    timeout(time: timeoutInSeconds, unit: 'SECONDS') {
                    env.Instance_IP = input message: 'User input required', ok: 'Select!',
                            parameters: [choice(name: 'instance', choices: ['draas', 'awsmarketplace', 'ibm bleeding edge', 'ibm pre-production','ibm production'], description: 'Select instance?')]
                    }
                    }catch (err) {
                       long timePassed = System.currentTimeMillis() - startTime
                       if (timePassed >= timeoutInSeconds * 1000) {
                           echo 'Timed out'
                           
                       } else {
                       throw err
                       }
                    }
                       def instance = "${env.Instance_IP}"
                      if (instance == 'draas'){
                      env.Instance_IP='DRAAS IP'
                      }
                      else if (instance == 'awsmarketplace'){
                       env.Instance_IP='AWS Market IP'
                      }
                      
                     }
                     echo "${env.Instance_IP}"

            }
        }
    }
}
