# doosra-vpc-be

## Configuration files and helper scripts
| Files               | Description                                         |
|-------------------- |-----------------------------------------------------|
| requirements.txt    | app depenedencies                                   |
| config.py           | configuration settings                              |
| manage.py           | helper script for app start and DB migrations       |


VPC+ helps you migrate your applications from an on-prem/public cloud to the Virtual Private Cloud of your choice.
VPC+ is part of the Wanclouds Automation Suite and assists enterprises in multi-cloud migrations. It gives you a 
one-stop solution to create, deploy, migrate, and manage your VPC infrastructure on public clouds like IBM Cloud,
Google Cloud Platform, Amazon Web Services, etc. Cloud migration is a tedious and painful process that takes 
time, resources, and specialized expertise that many enterprises do not have. VPC+ automates that process and 
accelerates your cloud migration from any to any cloud, reducing the migration time from weeks to hours.

## Setup Local Environment For IBM (without auth-delegation-svc):
### Prerequisites:
#### 1. Update and upgrade your system:
```shell
$ sudo apt-get update
$ sudo apt-get upgrade
```
#### 2. Install using repository:
```shell
$ sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
$ echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
#### 3. Install docker engine and version check:
```shell
$ sudo apt-get update
$ sudo apt-get install docker-ce docker-ce-cli containerd.io
$ docker --version
```
#### 4. Enable docker and status check:
```shell
$ sudo systemctl enable --now docker
$ sudo systemctl status docker (for quitting press “q” or “ctrl + c”)
```
#### 5. Install docker-compose and version check:
```shell
$ sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
$ sudo chmod +x /usr/local/bin/docker-compose
$ docker-compose --version
```
#### 6. Login to docker:
```shell
$ docker login
```
#### 7. Clone following repos:
```shell
$ git clone -b k8s_disaster_recovery https://github.com/Wanclouds/doosra-vpc-be.git 
$ git clone -b develop https://github.com/Wanclouds/doosra-Frontend.git 
```
### Before Environment Setup:
#### 8. Edit docker-compose.yml file
```bash
1. In imageworker service change value of WEBHOOK_BASE_URL to localhost:3000/
2. In web service after entrypoint add following: 
      ports:
         - "8081:8081"
3. Comment following services completely:
  app, nginx
```
#### 9. Start docker-compose.yml file
```shell
$ sudo docker-compose up --build
```
Or
```shell
$ docker-compose up -d --f
```
  
## Environment variables details
### webdb service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| MYSQL_DATABASE      | doosradb                                            | String  |
| MYSQL_USER          | webuser                                             | String  |
| MYSQL_PASSWORD      | admin123                                            | String  |
| MYSQL_ROOT_PASSWORD | admin123                                            | String  |

### rabbitmq service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| RABBIT_ENV_RABBITMQ_USER      | doosradb                                  | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD  | webuser                                   | String  |

### worker service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| VPCPLUS_LINK        | https://migrate-test.wanclouds.net/                 | String  |
| GOOGLE_OAUTH_LINK          | https://migrate-test.wanclouds.net/          | String  |
| RABBIT_ENV_RABBITMQ_USER   | guest                                        | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD | guest                                      | String  |
| FLASK_CONFIG        | development                                         | String  |
| GENERATION          | 2                                                   | Int     |
| LOKI_URL            | ${LOKI_URL}                                         | String  |
| LOKI_USERNAME       | 'admin'                                             | String  |
| LOKI_PASSWORD       | 'admin'                                             | String  |
| TAGS                | 'worker'                                            | String  |
| LOKI_LOGGING        | 'disabled'                                          | String  |
| SLACK_LOGGING       | 'disabled'                                          | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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'  | String  |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                             | String  |
| DEPLOYED_INSTANCE   | "None"                                              | String  |

### imageworker service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| SL_USERNAME         | danny@wanclouds                                     | String  |
| SL_API_KEY          | a65d423fa9ec1dff9bf9806d3c3e5d09e1f1a394d9289db418e7c72633244cb9 | String  |
| WEBHOOK_BASE_URL    | https://migrate-test.wanclouds.net/v1/ibm/image_conversion/      | String  |
| RABBIT_ENV_RABBITMQ_USER | guest                                         | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD          | guest                            | Int     |
| FLASK_CONFIG        | development                                        | String  |
| LOKI_URL            | ${LOKI_URL}                                        | String  |
| LOKI_USERNAME       | 'admin'                                            | String  |
| LOKI_PASSWORD       | 'admin'                                            | String  |
| TAGS                | 'imageworker'                                      | String  |
| LOKI_LOGGING        | 'disabled'                                         | String  |
| SLACK_LOGGING       | 'disabled'                                         | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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'  | String |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                            | String  |
| DEPLOYED_INSTANCE   | "None"                                             | String  |

### beatworker service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| RABBIT_ENV_RABBITMQ_USER     | guest                                      | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD | guest                                      | String  |
| FLASK_CONFIG    | development                                             | String  |
| GENERATION      | 2                                                       | Int     |
| REDIS           | beatredis                                               | String  |
| LOKI_URL        | ${LOKI_URL}                                             | String  |
| LOKI_USERNAME   | 'admin'                                                 | String  |
| LOKI_PASSWORD   | 'admin'                                                 | String  |
| TAGS            | 'beatworker'                                            | String  |
| LOKI_LOGGING    | 'disabled'                                              | String  |
| BEAT_WORKER_CONCURRENCY      | 100                                        | Int     |
| SLACK_LOGGING       | 'disabled'                                          | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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' | String |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                            | String  |
| DEPLOYED_INSTANCE   | "None"                                             | String  |

### emailworker service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| RABBIT_ENV_RABBITMQ_USER     | guest                                      | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD | guest                                      | String  |
| LOKI_URL        | ${LOKI_URL}                                             | String  |
| LOKI_USERNAME   | 'admin'                                                 | String  |
| LOKI_PASSWORD   | 'admin'                                                 | String  |
| TAGS            | 'emailworker'                                           | String  |
| LOKI_LOGGING    | 'disabled'                                              | String  |
| SLACK_LOGGING   | 'disabled'                                              | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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' | String |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                            | String  |
| DEPLOYED_INSTANCE   | "None"                                             | String  |

### web service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| ADMIN_APPROVAL_REQUIRED |  'False'                                        | String  |
| CONSUMPTION_APP         |  'True'                                         | String  |
| CONSUMPTION_APP_HOST    |  'https://consumption.wanclouds.net'            | String  |
| CONSUMPTION_APP_VERSION |  'v1'                                           | String  |
| CONSUMPTION_APP_API_KEY |  'testKey'                                      | String  |
| VPCPLUS_LINK            |  https://migrate-test.wanclouds.net/            | String  |
| GOOGLE_OAUTH_LINK       |  https://migrate-test.wanclouds.net/            | String  |
| RABBIT_ENV_RABBITMQ_USER     | guest                                      | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD | guest                                      | String  |
| FLASK_CONFIG    | development                                             | String  |
| GENERATION      | 2                                                       | Int     |
| LOKI_USERNAME   | 'admin'                                                 | String  |
| LOKI_PASSWORD   | 'admin'                                                 | String  |
| LOKI_URL        | ${LOKI_URL}                                             | String  |
| TAGS            | 'web'                                                   | String  |
| LOKI_LOGGING    | 'disabled'                                              | String  |
| SLACK_LOGGING   | 'disabled'                                              | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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' | String |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                             | String  |
| DEPLOYED_INSTANCE   | "None"                                             | String  |
| DB_MIGRATION_API_KEY| "abc123!"                                           | String  |
| DB_MIGRATION_CONTROLLER_HOST  |  "http://dbmigration-engg.wanclouds.net"  | String  |

### app service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| API_URL             | http://web:8081                                     | String  |
| PORT                | 3000                                                | Int     |

### scheduler service
| Env variable Name   | Default value                                       | Type    |
|-------------------- |-----------------------------------------------------|---------|
| RABBIT_ENV_RABBITMQ_USER     | guest                                      | String  |
| RABBIT_ENV_RABBITMQ_PASSWORD | guest                                      | String  |
| GENERATION                   | 2                                          | Int     |
| LOKI_URL        | ${LOKI_URL}                                             | String  |
| LOKI_USERNAME   | 'admin'                                                 | String  |
| LOKI_PASSWORD   | 'admin'                                                 | String  |
| TAGS            | 'scheduler'                                             | String  |
| LOKI_LOGGING    | 'disabled'                                              | String  |
| SLACK_LOGGING   | 'disabled'                                              | String  |
| SLACK_WEBHOOK_URL   | 'https://hooks.slack.com/services/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' | String |
| SLACK_CHANNEL       | '#vpc_bleeding_channel'                            | String  |
| DEPLOYED_INSTANCE   | "None"                                             | String  |
