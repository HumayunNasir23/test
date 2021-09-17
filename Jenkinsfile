pipeline {
    agent any
    stages {
        stage('Example') {
            steps {
                echo "Running ${env.BUILD_ID} on ${env.JENKINS_URL}"
 
            }
        }
        stage('SSH into the server') {
            steps {
                script {
                    def remote = [:]
                    remote.name = 'hu-jenkins-testing-do-not-delete'
                    remote.host = '163.69.83.205'
                    remote.user = 'root'
                    remote.identity = '-----BEGIN OPENSSH PRIVATE KEY-----
                                       b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
                                       NhAAAAAwEAAQAAAYEAz3ZOIQQRAvRsakGLl5ss1irCt9XNSq4RT7L6lXIHllpDo9vTXVJZ
                                       2P+7vtuctKk32r/r43YaoHrTnepHgRGkMTPP0kGWNb6D6UNpNLlDPcXfzo+WVor34mLNwE
                                       cP+Wv0/7arGfAdJ8N16tGue9SseHNSDit/j/GoppqHUwPfigCTAwEeWdC5wmcQnzZfUtyx
                                       Lg8/t/dCCiA4Tj4n23JTUiw5RJFpN7ZCWCuSxusj5WcvJx3yiT26Wz/ZPfQGIUkgc6Myb9
                                       6JdVopROWTVth17lM7gefrNIO2CadUlaH84y5FFHergGkCa2ej9L6NEbjCTuv2MzT5f84z
                                       Jo7zlKvIDM6oai9dppIscJC69pDgmSy0XCVwXSOtUf6bpCteyic2BLXxn9UmXL6oEy4PNe
                                       JVMHNfQSWt+BZK5TbZKKa6yjFbt8AwP+isYO26qJNyKrQGei5Ed+qXMRgDg3V6gbvZK2Af
                                       XvFTS3bKsL4h/QAZCmgwhinCt9WBGVk+9gTc6VO7AAAFmDkDsSM5A7EjAAAAB3NzaC1yc2
                                       EAAAGBAM92TiEEEQL0bGpBi5ebLNYqwrfVzUquEU+y+pVyB5ZaQ6Pb011SWdj/u77bnLSp
                                       N9q/6+N2GqB6053qR4ERpDEzz9JBljW+g+lDaTS5Qz3F386PllaK9+JizcBHD/lr9P+2qx
                                       nwHSfDderRrnvUrHhzUg4rf4/xqKaah1MD34oAkwMBHlnQucJnEJ82X1LcsS4PP7f3Qgog
                                       OE4+J9tyU1IsOUSRaTe2QlgrksbrI+VnLycd8ok9uls/2T30BiFJIHOjMm/eiXVaKUTlk1
                                       bYde5TO4Hn6zSDtgmnVJWh/OMuRRR3q4BpAmtno/S+jRG4wk7r9jM0+X/OMyaO85SryAzO
                                       qGovXaaSLHCQuvaQ4JkstFwlcF0jrVH+m6QrXsonNgS18Z/VJly+qBMuDzXiVTBzX0Elrf
                                       gWSuU22SimusoxW7fAMD/orGDtuqiTciq0BnouRHfqlzEYA4N1eoG72StgH17xU0t2yrC+
                                       If0AGQpoMIYpwrfVgRlZPvYE3OlTuwAAAAMBAAEAAAGAd5BNEsYPL87CNLK1ypgJzRwzwF
                                       Mdz25mV7JkrIBdUw+Ob/8e32e4lFE+WI6kz5G+uPlm715/lgFzuEzvDLmoERs1KI3YDf1Q
                                       dLz/Av3KfO1vQNKL6DCLEBO1VJ0f3bWUK1ORZI93nhUN/lj94Cv/giOkJLp49/JkKjBg0T
                                       0oNZaDI3Yfkc+zXxCbCccCRPUfv9XV+SYtDzzmdmFoAxbuYitOje/n3c3SipICM1YNCAbh
                                       q/+cafADWNeBUi0y4zgKzAUfRt8oUiTTkLBfpJe8D/CKNdcyswbwtYJBk/mcesdBs7Ib/L
                                       W2cjyfBahWF7du1PAKT6Ej5cIZ7l4V0+7TZxKXmUkiOnARwY6q7+KJh2g+p3g3VYNg3dwY
                                       6Kq2UfpDl/zsmDr7pH2FY4MINqlNctr8lk2ObXjX1uT6u1bzy8+FPV3hnFTCJanR8v6O8H
                                       MJ0l3jC/MGSq2oB91Kff3Hrfkotqr8yx0TBlB5QEDdQKLl7pT1k6RCQqys0hWbRsfBAAAA
                                       wQCtyYD5+oX5t5bvJ1R999DJBW8ehkFIs3iFwpD1uDgJ7gkYxb+UI3E1Lnh02JamhP6Haj
                                       q9cWn6VFJR3rSBIjDcJKtQD6cCV1dr6mpyxAkgwAx6zv0tbQlFqRQjGs00uQLzvXwrtGG+
                                       ALD3L08/zqjpe5QQx7vXrLDxHzfdFg6J9TicBPoX6eY5TVjdWT06bNqUwOSvmTYsKYecJ3
                                       3cZnXXYNzFLVRZ8L+kc34Y1Z3K6aCwqXAuL2tX4JphlZL9u8MAAADBAO+AL0IYLn2q4aYh
                                       LDKfSCUpZNllfGurTbk/rrG0mQwn+QVH6jIsWszJ9taAk6j9PGEizAQFIjnrKtd1fqXH4J
                                       akKIkvkNEz8NEur755GKI2wXl0y24E+9cvm5K5q1iB2mQWsxt6upDEtLHfIFD37F8MlW/h
                                       E8Y5bj6EtSFLk9iwLeN+7/4MhWZUd+FaivZdzaM2PwK0tltc68lQrWhSB7G7aMijWz2vFa
                                       /ZfvMeZlyU/cK0TAOWTu8o87S4gvWi6wAAAMEA3cEXL+ZvBWwj4/uxyU8s5LDoJH6GaSF5
                                       g2UeiOfzeU1TbVwHv8ubDcQEUf0ZJIluVuCihVLfQ8kkoyUWFWXMt4Eyi1Xo0L5a89GaqY
                                       DzUPjqxH7ZP1n4TM6129/cmC5Qe5/8XupGfrbgtPU5JBoqYRNlsxsCJY8f3LytEzS2w7fN
                                       Ly3cFDcfHRyeV3cjUTlmlK7rUtGvq5YfE9w1MteRVMQheanQDNh89GXru6oOFrRlVHVeIx
                                       RjOu/r1MSmNr5xAAAAHmh1bWF5dW5AaHVtYXl1bi1IUC1aQm9vay0xNy1HMwECAwQ=
                                       -----END OPENSSH PRIVATE KEY-----'
                    remote.allowAnyHosts = true
                    sshCommand remote: remote, command: "ls"

                }
            }
        }
    }
}
