# Name consts
NETWORK_INTERFACE_NAME = "vpc-network-interface-{}-{}"
VOLUME_NAME = "{}-volume"
VOLUME_ATTACHMENT_NAME = "{}-volume-attachment"

INVALID_INSTANCE = "INSTANCE with ID '{}' not found for user '{}'"
INSTANCE_CREATE = "Task for INSTANCE creation initiated by user: email '{}'"
INSTANCE_DELETE = "Task for INSTANCE deletion initiated by user: email '{}'"

IBM_GEN2_WINDOWS_REQ_STRING = (
    '#ps1_sysnative\n$fileStr="[DEFAULT]"\n$fileStr=$fileStr + "`r`n" +"#  `"cloudbase-init.conf`" '
    'is used for every boot"\n$fileStr=$fileStr + "`r`n" +"config_drive_types=vfat"\n$fileStr=$fileStr + "`r`n"'
    ' +"config_drive_locations=hdd"\n$fileStr=$fileStr + "`r`n" +"activate_windows=true"\n$fileStr=$fileStr + "`r`n" '
    '+"kms_host=kms.adn.networklayer.com:1688"\n$fileStr=$fileStr + "`r`n" +"mtu_use_dhcp_config=false"'
    '\n$fileStr=$fileStr + "`r`n" +"real_time_clock_utc=false"\n$fileStr=$fileStr + "`r`n" +"bsdtar_path=C:\\Program '
    'Files\\Cloudbase Solutions\\Cloudbase-Init\\bin\\bsdtar.exe"\n$fileStr=$fileStr + "`r`n" +"mtools_path=C:\\Program '
    'Files\\Cloudbase Solutions\\Cloudbase-Init\\bin\\"\n$fileStr=$fileStr + "`r`n" +"debug=true"\n$fileStr=$fileStr '
    '+ "`r`n" +"og_dir=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\log\\"\n$fileStr=$fileStr + "`r`n" '
    '+"log_file=cloudbase-init.log"\n$fileStr=$fileStr + "`r`n" +"default_log_levels=comtypes=INFO,suds=INFO,'
    'iso8601=WARN,requests=WARN"\n$fileStr=$fileStr + "`r`n" +"local_scripts_path=C:\\Program Files\\Cloudbase '
    'Solutions\\Cloudbase-Init\\LocalScripts\\"\n$fileStr=$fileStr + "`r`n" +"metadata_services=cloudbaseinit.'
    'metadata.services.configdrive.ConfigDriveService,"\n$fileStr=$fileStr + "`r`n" +"# enabled plugins - executed '
    'in order"\n$fileStr=$fileStr + "`r`n" +"plugins=cloudbaseinit.plugins.common.mtu.MTUPlugin,"\n$fileStr=$fileStr +'
    ' "`r`n" +"       cloudbaseinit.plugins.windows.ntpclient.NTPClientPlugin,"\n$fileStr=$fileStr + "`r`n" +"      '
    ' cloudbaseinit.plugins.windows.licensing.WindowsLicensingPlugin,"\n$fileStr=$fileStr + "`r`n" +"      '
    ' cloudbaseinit.plugins.windows.extendvolumes.ExtendVolumesPlugin,"\n$fileStr=$fileStr + "`r`n" +"      '
    ' cloudbaseinit.plugins.common.userdata.UserDataPlugin,"\n$fileStr=$fileStr + "`r`n" +"       '
    "cloudbaseinit.plugins.common.localscripts.LocalScriptsPlugin\"\n\n$cloudInintPath='C:\\Program Files\\Cloudbase "
    "Solutions\\Cloudbase-Init\\conf\\'\n$cloudbaseInit='cloudbase-init.conf'\nRemove-Item "
    "$cloudInintPath$cloudbaseInit\nNew-Item -Path $cloudInintPath -Name $cloudbaseInit -ItemType 'file' "
    '-Value $fileStr\n\n$str2 = "[DEFAULT]"\n$str2=$str2 + "`r`n" +"#  cloudbase-init-unattend.conf is used '
    'during the Sysprep phase"\n$str2=$str2 + "`r`n" +"username=Administrator"\n$str2=$str2 + "`r`n" '
    '+"inject_user_password=true"\n$str2=$str2 + "`r`n" +"first_logon_behaviour=no"\n$str2=$str2 + '
    '"`r`n" +"config_drive_types=vfat"\n$str2=$str2 + "`r`n" +"config_drive_locations=hdd"\n$str2=$str2 +'
    ' "`r`n" +"allow_reboot=false"\n$str2=$str2 + "`r`n" +"stop_service_on_exit=false"\n$str2=$str2 +'
    ' "`r`n" +"mtu_use_dhcp_config=false"\n$str2=$str2 + "`r`n" +"bsdtar_path=C:\\Program Files\\Cloudbase '
    'Solutions\\Cloudbase-Init\\bin\\bsdtar.exe"\n$str2=$str2 + "`r`n" +"mtools_path=C:\\Program Files\\Cloudbase '
    'Solutions\\Cloudbase-Init\\bin\\"\n$str2=$str2 + "`r`n" +"debug=true"\n$str2=$str2 + "`r`n" +"log_dir=C:\\Program '
    'Files\\Cloudbase Solutions\\Cloudbase-Init\\log\\"\n$str2=$str2 + "`r`n" +"log_file=cloudbase-init-unattend.log"'
    '\n$str2=$str2 + "`r`n" +"default_log_levels=comtypes=INFO,suds=INFO,iso8601=WARN,requests=WARN"\n'
    '$str2=$str2 + "`r`n" +"local_scripts_path=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\LocalScripts\\'
    '"\n$str2=$str2 + "`r`n" +"metadata_services=cloudbaseinit.metadata.services.configdrive.ConfigDriveService,'
    '"\n$str2=$str2 + "`r`n" +"# enabled plugins - executed in order"\n$str2=$str2 + "`r`n" '
    '+"plugins=cloudbaseinit.plugins.common.mtu.MTUPlugin,"\n$str2=$str2 + "`r`n" +"       '
    'cloudbaseinit.plugins.common.sethostname.SetHostNamePlugin,"\n$str2=$str2 + "`r`n" +"       '
    'cloudbaseinit.plugins.windows.createuser.CreateUserPlugin,"\n$str2=$str2 + "`r`n" +"       '
    'cloudbaseinit.plugins.windows.extendvolumes.ExtendVolumesPlugin,"\n$str2=$str2 + "`r`n" +"       '
    'cloudbaseinit.plugins.common.setuserpassword.SetUserPasswordPlugin,"\n$str2=$str2 + "`r`n" +"      '
    " cloudbaseinit.plugins.common.localscripts.LocalScriptsPlugin\"\n\n$cloudbaseInitUnattend='cloudbase-init-unattend.conf"
    "'\nRemove-Item $cloudInintPath$cloudbaseInitUnattend\nNew-Item -Path $cloudInintPath -Name $cloudbaseInitUnattend -ItemType "
    '\'file\' -Value $str2\n\n$pass= ConvertTo-SecureString "migration" -AsPlainText -Force\n$username = "migration"\nNew-LocalUser $username '
    '-Password $pass -FullName "wanclouds migration" -Description "Windows migration by Wanclouds Inc"\nAdd-LocalGroupMember -Group "Administrators" '
    "-Member $username\n\n# Add this on destination side\n$source=\"C:\\Users\\$username\\Administrator\\\"\n$destination='C:\\Users\\Administrator\\'\n# "
    "change source and destination here\n#copy data back\n\n$credential = New-Object System.Management.Automation.PSCredential "
    "$username, $pass\nStart-Process Notepad.exe -Credential $credential\n\nGet-ChildItem -Path $destination -Recurse |"
    " Move-Item -Destination $source\n\nmkdir $destination\\Desktop\nmkdir $destination\\Downloads\n\n$file='C:\\\\Program Files\\\\Cloudbase "
    "Solutions\\\\Cloudbase-Init\\\\conf\\\\Unattend.xml'\n((Get-Content -path $file -Raw) -replace "
    "'<PersistAllDeviceInstalls>true</PersistAllDeviceInstalls>','<PersistAllDeviceInstalls>false</PersistAllDeviceInstalls>') | Set-Content -Path $file\n\n"
    "$certificate='-----BEGIN CERTIFICATE-----\nMIIE1jCCA76gAwIBAgIQXRDLGOs6eQCHg6t0d/nTGTANBgkqhkiG9w0BAQsFADCB\nhDELMAkGA1UEBhMCVVMxHTAbBgNVBAoTFFN5bWFudGVjIENvcnBvcmF0aW9uMR8w\nHQYDVQQLExZTeW1hbnRlYyBUcnVzdCBOZXR3b3JrMTUwMwYDVQQDEyxTeW1hbnRl\nYyBDbGFzcyAzIFNIQTI1NiBDb2RlIFNpZ25pbmcgQ0EgLSBHMjAeFw0xODExMjcw\nMDAwMDBaFw0yMjAxMjUyMzU5NTlaMGgxCzAJBgNVBAYTAlVTMRcwFQYDVQQIDA5O\nb3J0aCBDYXJvbGluYTEQMA4GA1UEBwwHUmFsZWlnaDEWMBQGA1UECgwNUmVkIEhh\ndCwgSW5jLjEWMBQGA1UEAwwNUmVkIEhhdCwgSW5jLjCCASIwDQYJKoZIhvcNAQEB\nBQADggEPADCCAQoCggEBAN6tLWiLXZXnYDRc6y9qeQrnN59qP5xutjQ4AHZY/m9E\naNMRzKOONgalW6YTQRrW6emIscqlweRzvDnrF4hv/u/SfIq16XLqdViL0tZjmFWY\nhijbtFP1cjEZNeS47m2YnQgTpTsKmZ5A66/oiqzg8ogNbxxilUOojQ+rjzhwsvfJ\nAgnaGhOMeR81ca2YsgzFX3Ywf7iy6A/CtjHIOh78wcwR0MaJW6QvOhOaClVhHGtq\n8yIUA7k/3k8sCC4xIxci2UqFOXopw0EUvd/xnc5by8m7LYdDO048sOM0lASt2d4P\nKniOvUkU/LpqiFSYo/6272j+KRBDYCW2IgPCK5HWlZMCAwEAAaOCAV0wggFZMAkG\nA1UdEwQCMAAwDgYDVR0PAQH/BAQDAgeAMCsGA1UdHwQkMCIwIKAeoByGGmh0dHA6\nLy9yYi5zeW1jYi5jb20vcmIuY3JsMGEGA1UdIARaMFgwVgYGZ4EMAQQBMEwwIwYI\nKwYBBQUHAgEWF2h0dHBzOi8vZC5zeW1jYi5jb20vY3BzMCUGCCsGAQUFBwICMBkM\nF2h0dHBzOi8vZC5zeW1jYi5jb20vcnBhMBMGA1UdJQQMMAoGCCsGAQUFBwMDMFcG\nCCsGAQUFBwEBBEswSTAfBggrBgEFBQcwAYYTaHR0cDovL3JiLnN5bWNkLmNvbTAm\nBggrBgEFBQcwAoYaaHR0cDovL3JiLnN5bWNiLmNvbS9yYi5jcnQwHwYDVR0jBBgw\nFoAU1MAGIknrOUvdk+JcobhHdglyA1gwHQYDVR0OBBYEFG9GZUQmGAU3flEwvkNB\n0Dhx23xpMA0GCSqGSIb3DQEBCwUAA4IBAQBX36ARUohDOhdV52T3imb+YRVdlm4k\n9eX4mtE/Z+3vTuQGeCKgRFo10w94gQrRCRCQdfeyRsJHSvYFbgdGf+NboOxX2MDQ\nF9ARGw6DmIezVvNJCnngv19ULo1VrDDH9tySafmb1PFjkYwcl8a/i2MWQqM/erne\ny9aHFHGiWiGfWu8GWc1fmnZdG0LjlzLWn+zvYKmRE30v/Hb8rRhXpEAUUvaB4tNo\n8ahQCl00nEBsr7tNKLabf9OfxXLp3oiMRfzWLBG4TavH5gWS5MgXBiP6Wxidf93v\nMkM3kaYRRj+33lHdchapyKtWzgvhHa8kjDBB5oOXYhc08zqbfMpf9vNm\n-----END CERTIFICATE-----'\n"
    "New-Item -Path 'C:\\Users\\Administrator\\Desktop' -Name 'virtio-certificate.cer' -ItemType 'file' -Value $certificate\nImport-Certificate -FilePath C:\\Users\\Administrator\\Desktop\\virtio-certificate.cer -CertStoreLocation Cert:\\LocalMachine\\TrustedPublisher\n\n$virtIODownloadLink='https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso'\n$virtIOpath='C:\\Users\\Administrator\\Downloads\\virtio-win.iso'\n#[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n[Net.ServicePointManager]::SecurityProtocol = \"tls12, tls11, tls\"\nInvoke-WebRequest -OutFile $virtIOpath -Uri $virtIODownloadLink\nMount-DiskImage $virtIOpath\n$partition_style = Get-DiskImage $virtIOpath\n$res = $partition_style | Get-Volume  -ErrorAction stop\n$r=$res.DriveLetter\n\nmsiexec.exe /i `\"${r}:\\virtio-win-gt-x64.msi`\" /quiet /norestart\n\nC:\\Windows\\System32\\Sysprep\\Sysprep.exe /oobe /generalize /shutdown '/unattend:C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\conf\\Unattend.xml'\n"
)

RESTORE_ADMIN_USER_DATA = (
    '#ps1_sysnative\n\n$RootFolder="C:\\Users\\migration\\Administrator"\n'
    '\ndo\n{\n    $i = Test-Path "C:\\Users\\Administrator"\n    sleep 2\n    get-date\n\n}'
    " until ($i -eq $True)\n\n$SubFolders = Get-ChildItem -Path $RootFolder"
    " -Directory\n\nForeach ($SubFolder in $SubFolders) {\n  "
    '  $src="C:\\Users\\migration\\Administrator\\$SubFolder"\n   '
    ' $dst="C:\\Users\\Administrator\\$SubFolder"\n    mkdir $dst\n   '
    " Get-ChildItem -Path $src -Recurse | Move-Item -Destination $dst\n   "
    " Remove-Item $src -Recurse -Force -Confirm:$false\n}\n\nGet-ChildItem -Path "
    '"C:\\Users\\migration\\Administrator\\" -Recurse | Move-Item -Destination '
    '"C:\\Users\\Administrator\\"\nRemove-LocalUser -Name "migration"'
)
