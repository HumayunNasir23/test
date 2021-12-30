CAPACITY = "capacity"
NAME = "name"
VOLUME = "volume"
MAX_SECONDARY_VOLUMES_LIMIT = 4
LARGEST_SECONDARY_VOLUMES_LIMIT = 16000
SMALLEST_SECONDARY_VOLUME_LIMIT = 10
SECONDARY_VOLUME_MIGRATION_THRESHOLD = 10
DISK_IDENTIFIER = 1
SVM_ENV = "svm"  # SVM means secondry volume migration

QEMU_CUSTOM_INSTALLATION = """
wget https://download.qemu.org/qemu-3.0.0-rc0.tar.xz
tar xvJf qemu-3.0.0-rc0.tar.xz
cd qemu-3.0.0-rc0
yum groupinstall -y "Development Tools"
yum install -y python3
yum install -y zlib-devel
yum install -y zlib-devel.x86_64 glib2-devel.x86_64 binutils-devel.x86_64 boost-devel.x86_64 autoconf.noarch libtool.x86_64 openssl-devel.x86_64 pixman-devel.x86_64
python-devel.x86_64 libfdt-devel
./configure
make
make install
cd && rm -rf qemu-3.0.0*
"""

DATA_MIG_REQUIREMENTS = """#!/bin/bash
ATTACHED_VOLUME_COUNT="{ATTACHED_VOLUME_COUNT}"
ATTACHED_VOLUMES_CAPACITY="{ATTACHED_VOLUMES_CAPACITY}"
INSTANCE_NAME="{{INSTANCE_NAME}}"
VOLUME_NAME="{VOLUME_NAME}"
REGION="{REGION}"
PACKAGES="{PACKAGES}"
BUCKET="{BUCKET}"
API_KEY="{API_KEY}"
VERSION="{VERSION}"
WEB_HOOK_URI="{WEB_HOOK_URI}"
REPORT_FILE="/root/wanclouds-vpc-secondary-volume-migration.log"
SVM_WORKING_DISK="{SVM_WORKING_DISK}"
vpc_api_endpoint="https://$REGION.iaas.cloud.ibm.com"
"""

DATA_MIG_SCRIPT = """
# return 0 if $pkg is installed in $?
function installation() {
  command -v $pkg || rpm -q $pkg || $pkg --version || dpkg -s $pkg
}

# a util function to convert int to float
function int_to_float() {
  if [[ $number =~ ^[+-]?[0-9]*$ ]]; then
    number="$number.0"
  elif [[ $number =~ ^[+-]?[0-9]+\\.?[0-9]*$ ]]; then
    number="$number"
  fi
}

# a util function to extract a device size in exact GB
function bytes_to_GB() {
  bytes=$(blockdev --getsize64 /dev/$disk)
  giga_bytes=$(bc <<<"$bytes / 1024^3")
}

function generate_ibm_iam_token() {
  # Generate a fresh token by taking API_KEY
  generate_acc_token=$(curl -X POST 'https://iam.cloud.ibm.com/identity/token' -d 'grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey='"$API_KEY")
  a=$(echo "$generate_acc_token" | awk -v FS="(access_token|refresh_token)" '{print $2}')
  access_token=${a:3:-3}
  iam_token="Bearer $access_token"
}

function download_cos_image() {
  img_downloaded=false
  cd $download_path || return
  i=0
  #img_downloaded=false
  while ((i < 10)); do
    download_start_time=$(date +%s)
    echo "$VHD_FILE started DOWNLOADING at: $(date)" >>$REPORT_FILE
    generate_ibm_iam_token
    wget -c -o download_status.log https://s3.direct."$REGION".cloud-object-storage.appdomain.cloud/"$BUCKET"/"$VHD_FILE" --header "Authorization: $iam_token"
    if [ $? -eq 0 ]; then
      img_downloaded=true
      break
    else
      img_downloaded=false
      sleep 60
    fi
    i=$((i + 1))
  done
  download_end_time=$(date +%s)
  total_download_time=$(($download_end_time - $download_start_time))
  if $img_downloaded; then
    echo "$VHD_FILE took $total_download_time seconds for DOWNLOADING.." >>$REPORT_FILE
    img_info=$(qemu-img info $VHD_FILE | grep -Po 'virtual size: \K.*G' || qemu-img info $VHD_FILE | grep -Po 'virtual size: \K.*T')
  fi
}

function extract_image_to_disk() {
  img_extracted=false
  cd $download_path || return
  echo "$VHD_FILE started EXTRACTING on /dev/$disk at: $(date)" >>$REPORT_FILE
  extraction_start_time=$(date +%s)
  extract_status=$(qemu-img convert -f vpc "$VHD_FILE" /dev/"$disk" 2>&1)
  extraction_end_time=$(date +%s)
  total_extraction_time=$(($extraction_end_time - $extraction_start_time))
  if [ -z "$extract_status" ]; then
    img_extracted=true
    cd $download_path && rm -rf $VHD_FILE
    echo "$VHD_FILE took $total_extraction_time seconds for EXTRACTION.." >>$REPORT_FILE
  fi
}

function return_disk_format() {
  while read line; do
    my_array=($(echo $line | tr " " "
"))
    disk_format=${my_array[1]}
  done < <(df -Th | grep "^/dev/$disk_")
}

function permanent_mount_to_etc_fstab_file() {
  # write disk and mount point to file ---/etc/fstab--- to mount disk permanent
  return_disk_format
  to_be_added="/dev/$disk_     /mnt/$disk_      $disk_format        defaults,nofail      0       0"
  echo "$to_be_added" >>/etc/fstab
}

function mount_disk_partitions() {
  partition_list=()
  while IFS= read -r line; do
    p_line=$(echo $line | while read -a array; do echo "${array[0]}"; done)
    partition=$(echo $p_line | cut -f3 -d"/")
    partition_list+=($partition)
  done < <(fdisk -l /dev/$disk | tail -n +9)

  if [ ${#partition_list[@]} -eq 0 ]; then
    echo "Issue with Filesystem of the disk /dev/$disk" >>$REPORT_FILE
  else
    for part in "${partition_list[@]}"; do
      mkdir /mnt/$part && mount /dev/$part /mnt/$part
      if [ $? -eq 0 ]; then
        disk_=$part
        permanent_mount_to_etc_fstab_file
        echo "Partition /dev/$part MOUNTED on /mnt/$part successfully...." >>$REPORT_FILE
      else
        echo "Error with Filesystem of partition $part in disk /dev/$disk" >>$REPORT_FILE
      fi
    done
  fi
  unset partition_list
}

function mount_disk() {
  mounted=false
  create_stats=$(mkdir /mnt/"$disk" 2>&1)
  if [ -z "$create_stats" ]; then
    mount_stats=$(mount /dev/"$disk" /mnt/"$disk" 2>&1)
    if [ -z "$mount_stats" ]; then
      mounted=true
    else
      mount_disk_partitions
      echo "Failed to Mount DISK: $disk Error: $mount_stats" >>$REPORT_FILE
    fi
  else
    echo "Failed to Create Mount Path with Error: $create_stats" >>$REPORT_FILE
  fi
}

function report_vpc_plus() {
  curl -X PATCH -H "Content-Type: application/json" -d '{"status":"'"$status"'"}' $WEB_HOOK_URI
  if [ "$status" = "FAILED" ] || [ "$status" = "SUCCESS" ]; then
    echo "--------------Volume Migration for $VHD_FILE took $TOTAL_VOLUME_MIG_TIME Seconds--------------------" >>$REPORT_FILE
    exit
  fi
}

function if_volume_attached() {
  generate_ibm_iam_token
  all_volumes=$(curl -X GET "$vpc_api_endpoint/v1/volumes/$volume_id?version=$VERSION&generation=2&limit=1000" -H "Authorization: $iam_token" | jq '.volume_attachments')
  if [ $all_volumes == [] ]; then
      return 1
  else
    return 0
  fi
}

# Detach a Volume from Instance, set Volume_attachment and instance_id
function get_volume_from_ibm_by_name() {
  generate_ibm_iam_token
  all_volumes=$(curl -X GET "$vpc_api_endpoint/v1/volumes?version=$VERSION&generation=2&limit=1000&name=$VOLUME_NAME" -H "Authorization: $iam_token" | jq '.volumes')
  volume_json=$(echo "${all_volumes}" | jq -c '.[]')
  volume_id=$(echo $volume_json | jq '.id' | tr -d '"')
  volume_attachment_id=$(echo ${volume_json[0]} | jq -c '.volume_attachments[0].id' | tr -d '"')
  instance_id=$(echo ${volume_json[0]} | jq -c '.volume_attachments[0].instance.id' | tr -d '"')
}

# Detach a Volume from Instance, set Volume_attachment and instance_id
function detach_volume_from_instance() {
  get_volume_from_ibm_by_name
  generate_ibm_iam_token
  volume_attachment_href="$vpc_api_endpoint/v1/instances/$instance_id/volume_attachments/$volume_attachment_id?version=$VERSION&generation=2"
  response=$(curl -X DELETE $volume_attachment_href -H "Authorization: $iam_token")
  echo $response >>$REPORT_FILE
  volume_attachment_href="$vpc_api_endpoint/v1/volumes/$volume_id?version=$VERSION&generation=2"
  # Wait for Volume to detach from Machine
  while if_volume_attached; do
    sleep 2
  done
  delete_volume_response=$(curl -X DELETE $volume_attachment_href -H "Authorization: $iam_token")
  echo "============================================================" >>$REPORT_FILE
  echo "$delete_volume_response" >>$REPORT_FILE
}
function return_unmounted_disk() {
  number=${img_info:0:-1}
  number=$(echo $number | xargs)
  unit=${img_info: -1}
  if [ "$unit" = "T" ]; then
    number=$(echo "$number"*1000 | bc)
  fi
  int_to_float
  val=$number
  for v in "${!unmounted_volumes[@]}"; do
    disk=$v
    bytes_to_GB
    number=$giga_bytes
    int_to_float
    if (($(bc <<<"$number == $val"))); then
      unset unmounted_volumes["$v"]
      break
    fi
    disk=""
  done
}

function from_image_to_disk() {
  #set download_path and VHD_FILE
  download_cos_image
  if ! $img_downloaded; then
    echo "$VHD_FILE Failed to DOWNLOAD..!" >>$REPORT_FILE
    return
  fi
  return_unmounted_disk
  if [ -z "$disk" ]; then
    echo "NO UNMOUNTED DISK for $img_info" >>$REPORT_FILE
    return
  fi
  extract_image_to_disk
  if ! $img_extracted; then
    echo "$VHD_FILE Failed to EXTRACT..!" >>$REPORT_FILE
    return
  fi
  mount_disk
  if ! $mounted; then
    return
  fi
  report_vpc_plus
}

# MIGRATION FLOW starts Here
#   Install Required Packages
#   FIND AND MOUNT LARGEST DISK AS A HELPER DISK (Keeping area for VHD images util it is unpacked)
#   Loop over the rest of disk and call from_image_to_disk
#   IBM Is supporting more than 4 Disks with all profiles now, so no need for the rest of two lines otherwise we have to check
#   if Max Volumes are attached then detach already done disks, create and attach another disk and migrate the last disk
#     ==> Otherwise only attach another disk and migrate the last disk

echo "*****************Secondary Volume Migration Report for VSI $INSTANCE_NAME**********************" >>$REPORT_FILE

PACKAGES=($PACKAGES)
for pkg in "${PACKAGES[@]}"; do
  installation
  if [ $? != 0 ]; then
    echo "Unable to install $pkg,Volume Migration Failed, This is an issue in primary Image...!" >>$REPORT_FILE
    status="FAILED" && report_vpc_plus
    exit
  fi
  echo "$pkg package installed ..." >>$REPORT_FILE
done

status="IN_PROGRESS" && report_vpc_plus

# shellcheck disable=SC2129
echo "===============Attach Disks===============" >>$REPORT_FILE
lsblk >>$REPORT_FILE
echo "==========================================" >>$REPORT_FILE

# Extract Unmounted Disks
declare -A unmounted_volumes
while read line; do
  my_array=($(echo "$line" | tr " " "
"))
  if [ -z "${my_array[6]}" ]; then
    mounted_=$(df | grep /dev/"${my_array[0]}")
    if [ -z "$mounted_" ]; then
      unmounted_volumes[${my_array[0]}]=${my_array[3]}
    fi
  fi
done < <(lsblk)

greater_volume="$SVM_WORKING_DISK"
img_info="$SVM_WORKING_DISK"
return_unmounted_disk
mounted=false
if ! [ -z $disk ]; then
  echo -y | mkfs.ext4 /dev/"$disk" && mount_disk
fi

if $mounted; then   
  echo "Working Disk (/dev/$disk) Mounted.. having size $greater_volume!" >>$REPORT_FILE
else
  # shellcheck disable=SC2129
  echo "Failed to mount working directory" >>$REPORT_FILE
  echo "Reasons: $create_stats, $mount_stats" >>$REPORT_FILE
  echo "Failed to migrate Secondary Volumes Data...." >>$REPORT_FILE
  echo "---------------------Ended-------------------------------" >>$REPORT_FILE
  status="FAILED" && report_vpc_plus
fi

download_path="/mnt/$disk"
ATTACHED_VOLUME_COUNT=($ATTACHED_VOLUME_COUNT)

OVER_ALL_VOLUME_MIG_START_TIME=$(date +%s)
for volume_count in "${ATTACHED_VOLUME_COUNT[@]}"; do
  VOLUME_MIG_START_TIME=$(date +%s)
  VHD_FILE=$INSTANCE_NAME"-""$volume_count"".vhd"
  echo "########################################################################" >>$REPORT_FILE
  echo "--------------Volume Migration for $VHD_FILE started --------------------" >>$REPORT_FILE
  from_image_to_disk
  VOLUME_MIG_END_TIME=$(date +%s)
  TOTAL_VOLUME_MIG_TIME=$(($VOLUME_MIG_END_TIME - $VOLUME_MIG_START_TIME))
  echo "--------------Volume Migration for $VHD_FILE took $TOTAL_VOLUME_MIG_TIME Seconds--------------------" >>$REPORT_FILE
done
echo "Detaching Helper Volume $VOLUME_NAME from Instance $INSTANCE_NAME" >> $REPORT_FILE
detach_volume_from_instance

TOTAL_NET_TIME=$(($(date +%s) - OVER_ALL_VOLUME_MIG_START_TIME))
echo "--------------TOTAL Volume Migration for $INSTANCE_NAME took $TOTAL_NET_TIME Seconds--------------------" >>$REPORT_FILE
echo "----------------------------Ended----------------------------------" >>$REPORT_FILE
status="SUCCESS" && report_vpc_plus
"""

WINDOWS_MIG_REQ = """
$global:vhds_index = @({VHDS_INDEX})
$global:region = "{REGION}"
$global:bucket = "{BUCKET}"
$global:api_key = "{API_KEY}"
$global:version = "{VERSION}"
$global:web_hook_url = "{WEB_HOOK_URI}"
$global:generation = {GENERATION}
$global:instance_name = "{{INSTANCE_NAME}}"
$global:instance_id = "{INSTANCE_ID}"
"""

WINDOWS_SVM_SCRIPT = """
#ps1_sysnative
workflow windows-svm-workflow{{ InlineScript{{
        {WINDOWS_MIG_REQ}
        $global:base_url = "https://$global:region.iaas.cloud.ibm.com"
        $global:vhds = @()
        $global:all_volumes = $null
        $global:temp_folder_path = "C:\\wanclouds_temp\\"
        $global:new_folder_path = "C:\\Users\\Administrator\\Desktop\\migrated_folder_path"
        $global:access_token = ""
        $global:report = @{{ "status" = "IN_PROGRESS"; "message" = ""; "start_time" = ""; "end_time" = ""; "duration" = ""; "instance_id" = $global:instance_id; "resources" = @(); "action" = ""; }}
        function Retry-Command{{ Param([scriptblock]$ScriptBlock)
            $Timeout = 3600
            $timer = [Diagnostics.Stopwatch]::StartNew()
            while ($timer.Elapsed.TotalSeconds -lt $Timeout)
            {{try
                {{$res = $ScriptBlock.Invoke()
                    $timer.Stop()
                    return $res}}
                catch{{ $error = $_.Exception.Message
                    Start-Sleep -Seconds 10}}}}
            $timer.Stop()
            if ($error) {{ throw $error }}
            throw "something went wrong" }}
        function Send-Response {{ $header = @{{ "Content-Type" = "application/json" }}
            $body = $global:report
            $res = Retry-Command -ScriptBlock {{ wget -Method PUT $global:web_hook_url -H $header -Body ($body | ConvertTo-Json) -UseBasicParsing -ErrorAction stop
                return $res }}}}
        function Attach-Volume {{ param($volume_id, $instance_id)
            $global:report.action = "Attaching volume $volume_id for instance $instance_id"
            Send-Response
            $url = "$global:base_url/v1/instances/$instance_id/volume_attachments?version=$global:version&generation=$global:generation"
            $header = @{{ "Content-Type" = "application/json"; "Authorization" = "Bearer $global:access_token" }}
            $body = @{{ "delete_volume_on_instance_delete" = $true; "name" = "attachment-" + $volume_id; "volume" = @{{ "id" = $volume_id; }}; }}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method POST $url -H $header -Body ($body | ConvertTo-Json) -UseBasicParsing -ErrorAction stop
                return ConvertFrom-Json -inputObject $res }}
            return $res }}
        function Detach-Volume {{ param($attachment_id, $instance_id)
            $global:report.action = "Detaching attachment $attachment_id for instance $instance_id"
            Send-Response
            $url = "$global:base_url/v1/instances/$instance_id/volume_attachments/${{attachment_id}}?version=$global:version&generation=$global:generation"
            $header = @{{ "Content-Type" = "application/json"; "Authorization" = "Bearer $global:access_token" }}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method DELETE $url -H $header -UseBasicParsing -ErrorAction stop
                return $res  }}}}
        function Delete-Volume {{  param($id)
            $global:report.action = "Deleting volume $id"
            Send-Response
            $url = "$global:base_url/v1/volumes/${{id}}?version=$global:version&generation=$global:generation"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method DELETE $url -H $header -UseBasicParsing -ErrorAction stop
                return $res }}}}
        function Get-VolumeByStatus{{param($volume_id, $status)
            $global:report.action = "Checking volume $volume_id for status $status"
            Send-Response
            $url = "$global:base_url/v1/volumes/${{volume_id}}?version=$global:version&generation=$global:generation"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $res = Retry-Command -ScriptBlock {{$res = wget -Method GET $url -H $header -UseBasicParsing -ErrorAction stop
                $volume = ConvertFrom-Json -inputObject $res
                if ($volume.status -eq $status) {{return $res}} else{{ Start-Sleep -Seconds 10}}}}}}
        function Get-All-Volumes {{ $global:report.action = "Get-Volumes"
            Send-Response
            $url = "$global:base_url/v1/volumes?version=$global:version&generation=$global:generation"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $new_volumes = @()
            While ($true) {{  Generate-Token
                $res = Retry-Command -ScriptBlock {{ $res = wget -Method GET $url -H $header -UseBasicParsing -ErrorAction stop
                     $volumes = ConvertFrom-Json -inputObject $res
                     return $volumes}}
                $new_volumes += $res.volumes
                if ($res.next.href){{ $url=$res.next.href + "&version=${{global:version}}&generation=${{global:generation}}" }}
                else {{ break }} }}
            $global:all_volumes = $new_volumes}}
         function Move-Logfile {{
          do
            {{ $i = Test-Path "C:\\Users\\Administrator"
                 sleep 5 }} until ($i -eq $True)
            Move-Item -Path C:\\migration_log.txt -Destination C:\\Users\\Administrator\\Desktop\\migration_log.txt }}
        function Create-Volume {{ param($details, $index, $volume_capacity = $null)
         if ($null -eq $volume_capacity) {{ $volume_capacity = $details.capacity }}
            $global:report.action = "Creating volume with details $details"
            Send-Response
            $url = "$global:base_url/v1/volumes?version=$global:version&generation=$global:generation"
            $header = @{{ "Content-Type" = "application/json"; "Authorization" = "Bearer $global:access_token" }}
            $body = @{{"name" = "volume-${{index}}" + ($details.volume_attachments.instance.id -replace '_', '-');"capacity" = $volume_capacity;"zone" = @{{"name" = $details.zone.name;}};"profile" = @{{"name" = $details.profile.name; }};"resource_group" = @{{"id" = $details.resource_group.id;}};}}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method POST $url -H $header -Body ($body | ConvertTo-Json) -UseBasicParsing -ErrorAction stop
                $volume = ConvertFrom-Json -inputObject $res
                return $volume }}
            return $res }}
        function Rename-Volume {{ param($id, $name)
            $global:report.action = "Renaming volume $id to $name"
            Send-Response
            $url = "$global:base_url/v1/volumes/${{id}}?version=$global:version&generation=$global:generation"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $body = @{{ "name" = $name; }}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method PATCH $url -H $header -Body ($body | ConvertTo-Json) -UseBasicParsing -ErrorAction stop
                return $res }} }}
        function Generate-Token {{  $global:report.action  = "Generating access token"
            Send-Response
            $url = "https://iam.cloud.ibm.com/identity/token"
            $header = @{{ "Content-Type" = "application/x-www-form-urlencoded" }}
            $body = @{{ grant_type = "urn:ibm:params:oauth:grant-type:apikey"; apikey = $global:api_key }}
            $res = Retry-Command -ScriptBlock {{ $res = wget -Method POST $url -H $header -Body $body -UseBasicParsing -ErrorAction stop
                $jsonobj = ConvertFrom-Json -inputObject $res
                $global:access_token = $jsonobj.access_token
                return }}}}
        function Set-Protocol {{ [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 }}
        function Initialize-Disks {{ param($partition_style="MBR", $disk_number)
            $global:report.action = "Initializing disk $disk_number with partition style $partition_style"
            Send-Response
            Initialize-Disk -Number $disk_number -PartitionStyle $partition_style }}
        function Get-LargeDisk {{ $disk = Get-Disk | Where-Object partitionstyle -eq 'raw' | Where-Object {{$_.size -ge 1000000000}} | Sort-Object -Property size -Descending | Select-Object -first 1
            if ($disk) {{ return $disk }} else {{ return $null }} }}
        function Get-DiskDetails  {{ param($disk_id)
            $global:report.action = "Getting volume object for $disk_id"
            Send-Response
            $global:all_volumes | ForEach-Object -Process {{ if (($_.volume_attachments -ne $null) -and ($_.volume_attachments.id -Match $disk_id)) {{ return $_ }} }} }}
        function Download-Vhd {{ param($vhd, $drive_letter)
            $global:report.action = "Downloading vhd $vhd in drive $drive_letter"
            Send-Response
            $url = "https://s3.$global:region.cloud-object-storage.appdomain.cloud/$global:bucket/$vhd.vhd"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $output = "${{drive_letter}}:\$vhd.vhd"
            $res = Retry-Command -ScriptBlock {{ $wc = New-Object System.Net.WebClient
                $wc.Headers["Authorization"] = "Bearer $global:access_token"
                $wc.DownloadFile($url, $output)
                return }} }}
        function Get-VhdSize {{ param($vhd)
            $global:report.action = "getting vhd $vhd size"
            Send-Response
            $url = "https://s3.$global:region.cloud-object-storage.appdomain.cloud/$global:bucket/$vhd.vhd"
            $header = @{{ "Authorization" = "Bearer $global:access_token" }}
            $res = Retry-Command -ScriptBlock {{ $res = Invoke-WebRequest $url -Method Head -Headers $header -UseBasicParsing -ErrorAction stop
                return $res.Headers.'Content-Length' }}
            $res = [int64]$res
            return $res }}
        function Migrator {{ param($partition_style, $disk_number, $base_drive_letter, $resource_name, $Actual_mounted_folder_path, $index)
            Initialize-Disks -disk_number $disk_number -partition_style $partition_style
            $target_drive = Get-Disk -Number $disk_number
            $mounted_vhd_drive = GET-DISKIMAGE "${{base_drive_letter}}:\$resource_name.vhd" | GET-DISK | GET-PARTITION -ErrorAction stop
            $partitions_count = $mounted_vhd_drive.count
            $counter = 0
            $reserved_size = 0
            if ($partition_style -eq "GPT") {{ $reserved_size = $target_drive | Get-Partition | Where-Object {{ $_.type -eq "reserved" }} | ForEach-Object -Process {{ $_.size }}
                $reserved_size = $reserved_size/($partitions_count - 1) }}
            foreach ($vhd_drive in $mounted_vhd_drive) {{ $counter = $counter + 1
                if ($vhd_drive.DriveLetter) {{ $file_system = $vhd_drive | GET-VOLUME | ForEach-Object -Process {{ $_.filesystem }} -ErrorAction stop
                    if ($file_system -eq "") {{ $file_system = "NTFS" }}
                    $vhd_drive_letter = $vhd_drive.DriveLetter
                    $vhd_drive_size = $vhd_drive.size - $reserved_size
                    if ($counter -eq $partitions_count) {{ $target_drive_letter = $target_drive | New-Partition -AssignDriveLetter -UseMaximumSize | Format-Volume -FileSystem $file_system -NewFileSystemLabel "disk" -Confirm:$false | ForEach-Object -Process {{ $_.DriveLetter }} -ErrorAction stop }} else {{ $target_drive_letter = $target_drive | New-Partition -AssignDriveLetter -Size $vhd_drive_size | Format-Volume -FileSystem $file_system -NewFileSystemLabel "disk" -Confirm:$false | ForEach-Object -Process {{ $_.DriveLetter }} -ErrorAction stop }}
                    if ($file_system -ne "") {{  Move-data -vhd_drive_letter $vhd_drive_letter -vhd $resource_name -destination_drive_letter $target_drive_letter -physical_drive_letter $base_drive_letter }} }}
                elseif($vhd_drive.type -ne "reserved") {{ $file_system = $vhd_drive | GET-VOLUME | ForEach-Object -Process {{ $_.filesystem }} -ErrorAction stop
                    if ($file_system -eq "") {{  $file_system = "NTFS" }}
                    $vhd_drive_size = $vhd_drive.size - $reserved_size
                    if ($counter -eq $partitions_count) {{ $partition = $target_drive | New-Partition -UseMaximumSize | Format-Volume -FileSystem $file_system -NewFileSystemLabel "disk" -Confirm:$false -ErrorAction stop
                        if (-Not($Actual_mounted_folder_path)) {{ 
                        do {{ $i = Test-Path "C:\\Users\\Administrator"
                         sleep 2 }} until ($i -eq $True)
                        New-Item -ItemType Directory -Path "${{global:new_folder_path}}-${{index}}\\"
                            $Actual_mounted_folder_path = "${{global:new_folder_path}}-${{index}}\\" }}
                        $target_drive | Get-Partition | Where-Object {{ $_.type -ne "reserved" }} | Add-PartitionAccessPath -AccessPath $Actual_mounted_folder_path }}
                    else {{ $partition = $target_drive | New-Partition -Size $vhd_drive_size | Format-Volume -FileSystem $file_system -NewFileSystemLabel "disk" -Confirm:$false -ErrorAction stop
                        if (-Not ($Actual_mounted_folder_path)) {{  New-Item -ItemType Directory -Path "${{global:new_folder_path}}-${{index}}\\"
                            $Actual_mounted_folder_path = "${{global:new_folder_path}}-${{index}}\\" }}
                        $target_drive | Get-Partition | Where-Object {{ $_.type -ne "reserved" }} | Add-PartitionAccessPath -AccessPath $Actual_mounted_folder_path }}
                    if ($file_system -ne "") {{ $global:report.action = "Moving contents of $resource_name from file folder path $global:temp_folder_path to path $Actual_mounted_folder_path"
                        Send-Response
                        Get-ChildItem -Path $global:temp_folder_path* | ForEach-Object {{ Copy-Item -Path $_ -Destination ${{Actual_mounted_folder_path}} }} -ErrorAction stop
                        $mounted_folder_partition | Remove-PartitionAccessPath -AccessPath $global:temp_folder_path
                        Remove-Item  -Path $global:temp_folder_path }} }} }}
            Remove-resource -vhd $resource_name -physical_drive_letter $base_drive_letter }}
        function Move-data {{ param($vhd_drive_letter, $vhd, $destination_drive_letter)
            $global:report.action = "Moving contents of $vhd from drive $vhd_drive_letter to drive $destination_drive_letter"
            Send-Response
            Get-ChildItem -Path ${{vhd_drive_letter}}:\* | ForEach-Object {{ Move-Item -Path $_ -Destination ${{destination_drive_letter}}:\ }} -ErrorAction stop}}
        function Set-Log {{ param($message)
            $message | Out-File -FilePath "C:\\migration_log.txt" -Append }}
        function Remove-resource {{ param($vhd, $physical_drive_letter)
            $global:report.action = "Removing $vhd from drive $physical_drive_letter"
            Send-Response
            DISMOUNT-DISKIMAGE "${{physical_drive_letter}}:\$vhd.vhd" -ErrorAction stop
            Remove-Item -Path "${{physical_drive_letter}}:\$vhd.vhd" -recurse -ErrorAction stop
            $global:vhds_migrated = $global:vhds_migrated + $vhd
            Clear-RecycleBin -Force }}
        function enable-rdp {{ $global:report.action = "Enabling RDP"
            Send-Response
            Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\\' -Name fDenyTSConnections -Value 0
            Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp\\' -Name 'UserAuthentication' -Value 1
            Enable-NetFireWallRule -DisplayGroup 'Remote Desktop' }}
        function enable-ping {{ $global:report.action = "Enabling ping"
            Send-Response
            Set-NetFirewallRule -DisplayName "File and Printer Sharing (Echo Request - ICMPv4-In)" -enabled True
            Set-NetFirewallRule -DisplayName "File and Printer Sharing (Echo Request - ICMPv6-In)" -enabled True }}
        function Lets-Migrate {{ $base_disk = Get-LargeDisk
            Initialize-Disks -disk_number $base_disk.number
            $base_partition = $base_disk | New-Partition -AssignDriveLetter -UseMaximumSize | Format-Volume -FileSystem NTFS -NewFileSystemLabel "disk" -Confirm:$false
            $base_drive_letter = $base_partition.DriveLetter
            $base_disk_initial_size = $base_disk.Size / 1gb
            $base_disk_initial_name = $null
            $base_drive_free_space = [int64](Get-CimInstance -ClassName Win32_LogicalDisk | Where-Object {{ $_.DeviceID -eq "${{base_drive_letter}}:" }}).FreeSpace
            $index = 0
            foreach ($resource in $global:report.resources) {{ $resource_name = $resource.name
                try {{  $start = (Get-Date)
                    $resource.start_time = Get-Date -Format "dddd MM/dd/yyyy HH:mm"
                    $resource.status = "IN_PROGRESS"
                     Generate-Token
                    $vhd_size = Get-VhdSize -vhd $resource_name
                    if ($base_drive_free_space -lt $vhd_size) {{ Get-All-Volumes
                        $temporary_base_drive_to_detach_volume_obj = Get-DiskDetails -disk_id $base_disk.serialnumber
                        Detach-Volume -attachment_id $temporary_base_drive_to_detach_volume_obj.volume_attachments.id -instance_id $temporary_base_drive_to_detach_volume_obj.volume_attachments.instance.id
                        Delete-Volume -id $temporary_base_drive_to_detach_volume_obj.id
                        $volume_capacity = ([math]::round($base_disk_initial_size)) + ((10 / 100) * $base_disk_initial_size)
                        $volume_capacity = [math]::round($volume_capacity)
                        if ($volume_capacity -gt 2000) {{ $volume_capacity = 2000 }}
                        $base_disk_initial_name = $temporary_base_drive_to_detach_volume_obj.name
                        $new_volume = Create-Volume -details $temporary_base_drive_to_detach_volume_obj -index $index -volume_capacity $volume_capacity
                        Get-VolumeByStatus -volume_id $new_volume.id -status "available"
                        Attach-Volume -volume_id $new_volume.id -instance_id $temporary_base_drive_to_detach_volume_obj.volume_attachments.instance.id
                        $Timeout = 600
                        $timer = [Diagnostics.Stopwatch]::StartNew()
                        while ($timer.Elapsed.TotalSeconds -lt $Timeout) {{ $base_disk = Get-LargeDisk
                            $new_size = $base_disk.Size/1gb
                            if ($base_disk -and $new_size -gt $base_disk_initial_size) {{ break }}
                            else {{ Start-Sleep -Seconds 30 }} }}
                        $timer.Stop()
                        Initialize-Disks -disk_number $base_disk.number
                        $base_partition = $base_disk | New-Partition -AssignDriveLetter -UseMaximumSize | Format-Volume -FileSystem NTFS -NewFileSystemLabel "disk" -Confirm:$false
                        $base_drive_letter = $base_partition.DriveLetter }}
                    Generate-Token
                    Set-Log -message "downloading ${{resource_name}}"
                    Download-Vhd -vhd $resource_name -drive_letter $base_drive_letter
                    Set-Log -message "download complete ${{resource_name}}"
                    MOUNT-DISKIMAGE "${{base_drive_letter}}:\$resource_name.vhd" -ErrorAction stop
                    $downloaded_vhd = GET-DISKIMAGE "${{base_drive_letter}}:\$resource_name.vhd" -ErrorAction stop
                    $downloaded_vhd_disk = $downloaded_vhd | Get-Disk
                    $partition_style = $downloaded_vhd_disk | ForEach-Object -Process {{ $_.partitionstyle }} -ErrorAction stop
                    $resource.size = ([math]::round($downloaded_vhd.filesize/1gb, 4)).ToString() + " GB"
                    $target_drive = Get-Disk | Where-Object partitionstyle -eq 'raw' | Where-Object {{ $_.size -eq $downloaded_vhd.size }} | Select-Object -first 1
                    $reserved_size = 0
                    $mounted_folder_partition = (Get-Partition -DiskNumber $downloaded_vhd_disk.number)
                    $access_paths = $mounted_folder_partition.AccessPaths
                    $Actual_mounted_folder_path = ""
                    if ($access_paths[1].toCharArray().Count -gt 3) {{ New-Item -ItemType Directory -Path $global:temp_folder_path
                        if (-Not ($access_paths[1].StartsWith("\\\\?\Volume{{"))) {{ $Actual_mounted_folder_path = $access_paths[1]
                            $mounted_folder_partition | Remove-PartitionAccessPath -AccessPath $access_paths[1] }}
                        $mounted_folder_partition | Add-PartitionAccessPath -AccessPath $temp_folder_path }}
                    if ($target_drive) {{ Set-Log -message "migrating ${{resource_name}}"
                    Migrator -partition_style $partition_style -disk_number $target_drive.number -base_drive_letter $base_drive_letter -resource_name $resource_name -Actual_mounted_folder_path $Actual_mounted_folder_path -index $index }}
                    else {{ Generate-Token
                        $all_drives = Get-Volume | Where-Object {{$_.DriveLetter -ne "C"}} | Where-Object {{$_.size -ge 1000000000}} | Get-Partition | Get-Disk | Where-Object {{$_.serialnumber}} | Sort-Object -Property serialnumber -Unique
                        Get-All-Volumes
                        $drive_to_detach = $base_disk
                        $drive_to_detach_volume_obj = Get-DiskDetails -disk_id $drive_to_detach.serialnumber
                        if ($all_drives.count -eq 4)  {{ $temporary_drive_to_detach = $all_drives | Where-Object {{ $_.serialnumber -ne $base_disk.serialnumber }} | Select-Object -first 1
                            $temporary_drive_to_detach_volume_obj = Get-DiskDetails -disk_id $temporary_drive_to_detach.serialnumber
                            Detach-Volume -attachment_id $temporary_drive_to_detach_volume_obj.volume_attachments.id -instance_id $temporary_drive_to_detach_volume_obj.volume_attachments.instance.id }}
                        $new_volume = Create-Volume -details $drive_to_detach_volume_obj -index $index -volume_capacity $base_disk_initial_size
                        Get-VolumeByStatus -volume_id $new_volume.id -status "available"
                        Attach-Volume -volume_id $new_volume.id -instance_id $drive_to_detach_volume_obj.volume_attachments.instance.id
                        $Timeout = 600
                        $timer = [Diagnostics.Stopwatch]::StartNew()
                        while ($timer.Elapsed.TotalSeconds -lt $Timeout) {{ $target_drive = Get-LargeDisk
                            if ($target_drive) {{ break }} else {{ Start-Sleep -Seconds 30 }} }}
                        $timer.Stop()
                        Set-Log -message "migrating ${{resource_name}}"
                        Migrator -partition_style $partition_style -disk_number $target_drive.number -base_drive_letter $base_drive_letter -resource_name $resource_name -Actual_mounted_folder_path $Actual_mounted_folder_path -index $index
                        Generate-Token
                        Detach-Volume -attachment_id $drive_to_detach_volume_obj.volume_attachments.id -instance_id $drive_to_detach_volume_obj.volume_attachments.instance.id
                        Delete-Volume -id $drive_to_detach_volume_obj.id
                        if ($all_drives.count -eq 4) {{ Attach-Volume -volume_id $temporary_drive_to_detach_volume_obj.id -instance_id $temporary_drive_to_detach_volume_obj.volume_attachments.instance.id }}
                        if ($null -eq $base_disk_initial_name) {{ $base_disk_initial_name = $drive_to_detach_volume_obj.name }}
                        Rename-Volume -id $new_volume.id -name $base_disk_initial_name }}
                    $resource.status="SUCCESS"
                    Set-Log -message "migrating ${{resource_name}} completed successfully"
                    $resource.end_time = Get-Date -Format "dddd MM/dd/yyyy HH:mm"
                    $end = (Get-Date)
                    $resource.duration = '{{0:hh}} hour {{0:mm}} min {{0:ss}} sec' -f ($end - $start)
                    Send-Response }}
                catch {{ $resource.status="FAILED"
                    $message = "migrating " + $resource.name + " failed due to " + $_.Exception.Message + " trace: " + $_.ScriptStackTrace
                    Set-Log -message $message
                    $resource.message=$_.Exception.Message
                    $resource.trace=$_.ScriptStackTrace
                    $resource.end_time = Get-Date -Format "dddd MM/dd/yyyy HH:mm"
                    $end = (Get-Date)
                    $resource.duration = '{{0:hh}} hour {{0:mm}} min {{0:ss}} sec' -f ($end - $start)
                    $resource.action=$global:report.action }}
                $index = $index + 1 }} }}
        function Initialize {{ $start = (Get-Date)
            $global:report.start_time = Get-Date -Format "dddd MM/dd/yyyy HH:mm"
            foreach($index in $global:vhds_index){{$global:vhds=$global:vhds + ($global:instance_name+"-"+$index)}}
            foreach ($vhd in $global:vhds) {{ $resource = @{{"status" = "PENDING";"message" = "";"name" = "";"size" = "";"download_speed" = "";"start_time" = "";"end_time" = "";"duration" = "";"eta" = "";"action" = "";"trace" = "";}}
                $resource.name = $vhd
                $global:report.resources = $global:report.resources + $resource }}
            Set-Protocol
            $global:report.action = "MIGRATION"
            Send-Response
            enable-rdp
            enable-ping
            $global:report.action = ""
            Set-Log -message "starting migration"
            Lets-Migrate
            $global:report.action = "MIGRATION"
            $global:report.status = "SUCCESS"
            $global:report.resources | ForEach-Object {{if ($_.status -eq "FAILED") {{$global:report.status = "FAILED" }}}}
            $global:report.end_time = Get-Date -Format "dddd MM/dd/yyyy HH:mm"
            $end = (Get-Date)
            $global:report.duration = '{{0:hh}} hour {{0:mm}} min {{0:ss}} sec' -f ($end - $start)
            $message = "migration " + $global:report.status
            Set-Log -message $message
            Move-Logfile
            Send-Response }}
        try {{ Initialize }}
        catch {{ $message = "migration failed failed due to " + $_.Exception.Message + " trace: " + $_.ScriptStackTrace
        Set-Log -message $message }} }} }}
windows-svm-workflow
"""

NAS_MIG_CONSTS = r"""#!/bin/bash
user_id="{user_id}"
migration_host="{migration_host}"
vpc_backend_host="{vpc_backend_host}"
src_migrator_name="{src_migrator_name}"
trg_migrator_name="{trg_migrator_name}"
instance_type="{instance_type}"
disks='{disks}'
"""

NAS_MIG_SCRIPT = r"""
report_file="/root/report.log"
function mount_disk_on_machine() {
    if [ $mount_point ]; then
        bash_array+=( "$mount_point" )
    fi
  mkdir $mount_point
  echo y | mkfs.$fstype /dev/$disk_or_partition || echo y | mkfs.ext4 /dev/$disk_or_partition
  mount /dev/$disk_or_partition $mount_point
}

function get_unmounted_disk() {
  disk=""
  # shellcheck disable=SC2068
  for d in ${!unmounted_disks[@]}; do
    if [ "$disk_size" == ${unmounted_disks[$d]} ]; then
      disk=$d
      unset unmounted_disks[$d]
      break
    fi
  done
}

function bash_array_to_python_list(){
    arr='[]'  # Empty JSON array
    for x in "${bash_array[@]}"; do
      arr=$(jq -n --arg x "$x" --argjson arr "$arr" '$arr + [$x]')
    done
}

(echo y | yum update && echo y | yum install jq bc) || (echo y | apt update && echo y | apt install jq bc)
# Extract Unmounted Disks
declare -A unmounted_disks
while read line; do
  my_list=($(echo "$line" | tr " " "
"))
  if [ -z "${my_list[6]}" ]; then
    mounted_=$(df | grep /dev/"${my_list[0]}")
#    mounted_c=$(blkid | grep /dev/"${my_list[0]}")
    if [ -z "$mounted_" ] && [ "${my_list[0]}" != "vda" ]; then
      unmounted_disks[${my_list[0]}]=${my_list[3]}
    fi
  fi
done < <(lsblk)


function find_extended_partition() {
  index_=0
  found=False
  for p in $(echo "$par" | jq -c '.[]'); do
      ((index_=index_+1))
        partype=$(echo "$p" | jq  '.parttype' | tr -d '"')
        sb_par=$(echo $p | jq '.partitions')
        if [ "Extended" = $partype ]; then
          found=True
          break
        elif ! [ $sb_par = "null" ]; then
          found=True
          break
        fi
      done
      if [ $index_ -gt 4 ]; then
        found=True
      fi
}

bash_array=()
for i in $(echo "${disks}" | jq -c '.[]'); do
    par=$(echo $i | jq '.partitions')
    disk_size=$(echo "$i" | jq  '.size' | tr -d '"')
    get_unmounted_disk
    dd if=/dev/zero of=/dev/$disk  bs=512  count=1
    if ! [ "$par" = "[]" ] && ! [ "$par" = "null" ]; then
      echo "#########################################################" >>$report_file
      i=0
      find_extended_partition
      if $found; then
        (echo n; echo e; echo ; echo ; echo ; echo w) | fdisk /dev/"$disk"
        i=4
      fi
      for p in $(echo "$par" | jq -c '.[]');do
          mount_point=$(echo "$p" | jq  '.mountpoint' | tr -d '"')
          part_size=$(echo "$p" | jq  '.size' | tr -d '"')
          fstype=$(echo "$p" | jq  '.fstype' | tr -d '"')
          echo "----------------">>$report_file
          echo $mount_point $disk_size $part_size $fstype>>$report_file
          echo "----------------">>$report_file
          if $found; then
            (echo n; echo ; echo +$part_size; echo w) | fdisk /dev/"$disk"
          else
            (echo n; echo p; echo ; echo ; echo +$part_size; echo w) | fdisk /dev/"$disk"
          fi
          ((i=i+1))
          disk_or_partition=$disk$i
          mount_disk_on_machine
        done
        echo "#########################################################">>$report_file
    else
        mount_point=$(echo "$i" | jq  '.mountpoint' | tr -d '"')
        fstype=$(echo "$i" | jq  '.fstype' | tr -d '"')
        echo "*******">>$report_file
        echo $mount_point $disk_size $fstype>>$report_file
        echo "*******">>$report_file
        disk_or_partition=$disk
        mount_disk_on_machine
    fi
done

"""

CONTENT_MIGRATOR_AGENT_DEPLOY_SCRIPT = r"""
# set -e
distro=$(awk -F= '/^ID=/{print $2}' /etc/os-release)
if [ "$distro" = '"centos"' ] || [ "$distro" = "rhel" ] || [ "$distro" = '"rhel"' ] || [ "$distro" = "centos" ]; then
  echo "~~~~~~~~~~"
  echo "RHEL or CentOS detected. Adding firewall exception."
  yum install firewalld -y
  systemctl start firewalld
  firewall-offline-cmd --add-port=7077/tcp
  systemctl restart firewalld
  systemctl enable firewalld
  echo "~~~~~~~~~~"
else
  echo "~~~~~~~~~~"
  echo "Neither RHEL nor CentOS detected. Not adding firewall exception."
  echo "~~~~~~~~~~"
fi
if [ ! -x /usr/bin/wget ] ; then
  echo y | apt install wget || echo y | yum install wget
else
  true
fi
if wget -O content-migrator https://agents.wanclouds.net/$instance_type/contentdirectory/content-migrator-linux; then
  true
fi
if test -e content-migrator; then
  echo "Agent Binary Downloaded Successfully"
else
  echo "Agent Binary Not Found"
fi
if [[ -x "content-migrator" ]]; then
  true
else
  echo "Making Agent Binary Executable"
  chmod +x content-migrator
fi
export USER_ID=$user_id
export NAME=$trg_migrator_name
export STORAGE_DISCOVERY=false
export PORT=7077
export MIGRATION_HOST=$migration_host
./content-migrator & disown
sleep 5
bash_array_to_python_list

echo "==========================="
echo $arr
echo $vpc_backend_host
echo $user_id
echo $src_migrator_name
echo $trg_migrator_name
echo "==========================="
curl -X PATCH "$vpc_backend_host"v1/migrate/content/start/"$user_id" -H "Accept: application/json" -H "Content-Type: application/json" --data-binary @- <<DATA
{
    "locations": $arr,
    "src_migrator": "$src_migrator_name",
    "trg_migrator": "$trg_migrator_name"
}
DATA
"""
