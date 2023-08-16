pipeline {
    agent any
    environment{
       VERSION = '1.1.0'
    } 
    stages {
        stage('Build') {
            steps {
                sh 'echo Build'
                sh 'ls'
                echo "Building version ${VERSION}"
            }
        }
        stage('Test') {
            when {
                expression { env.BRANCH_NAME == 'develop'}
            }
            steps {
                sh 'echo Test'
                sh 'pwd'
            }
        }
          stage ('Select instance for deployment') {
           steps{
               script{
                   long startTime = System.currentTimeMillis()
                   timeoutInSeconds = 30
                   try{
                      timeout(time: timeoutInSeconds, unit: 'SECONDS') {
                          env.Instance_IP = input message: 'User input required', ok: 'Select!',
                          parameters: [choice(name: 'instance', choices: ['draas', 'aws-marketplace', 'ibm-bleeding-edge', 'ibm-pre-production','ibm-production'], description: 'Select Instance to deploy?')]
                      }
                   }
                   catch (err) {
                       long timePassed = System.currentTimeMillis() - startTime
                       if(timePassed >= timeoutInSeconds * 1000) {
                           echo 'Timed out'
                           echo 'DRaaS instance IP will be used as default'
                           env.Instance_IP='163.69.83.20'
                           }
                       else {
                           throw err
                           }
                   }
                   def instance = "${env.Instance_IP}"
                   if (instance == 'draas'){
                      env.Instance_IP='163.69.83.20'
                   }
                   else if (instance == 'aws-marketplace'){
                       env.Instance_IP='AWS Marketplace IP'
                   }
                   else if (instance == 'ibm-bleeding-edge'){
                       env.Instance_IP='IBM Bleeding Edge IP'
                   }
                   else if (instance == 'ibm-pre-production'){
                       env.Instance_IP='IBM Pre-production IP'
                   }
                   else if (instance == 'ibm-production'){
                       env.Instance_IP='IBM production IP'
                   }
               }
           }
        }
        stage('Deploy') {
            steps {
                sh 'echo Deploy'
                sh 'touch newfile'
                script{
                   def environment = "staging"
                   if (environment == 'draas'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'aws-marketplace'){
                       echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'staging'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'ibm-pre-production'){
                      echo "Deploying on ${environment} instance"
                   }
                   else if (environment == 'ibm-production'){
                       echo "Deploying on ${environment} instance"
                   }
                }
            }
        }
        stage('Deploy New') {
            steps {
                sh 'echo Deploy'
            }
        }
    }
    post{
        always{
         sh 'echo Always EXECUTION!!!'
        }
    }
}

