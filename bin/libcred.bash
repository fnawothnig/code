#!bash
. lib.bash

# create a temporary file on RAM

mkcredfile() {
	mktemp --tmpdir=/dev/shm "credentials.$UID.XXXXXXXX"
}

# readcred(object, [printfmt])
# prompt user for username/password

readcred() {
	local OPT OPTARG OPTIND
	local nouser=false
	local fmt='username=%s\npassword=%s\n'
	local prompt=''
	local user=$LOGNAME
	local pass=
	while getopts 'Uf:p:u:' OPT; do
		case $OPT in
			U)	nouser=true	;;
			f)	fmt=$OPTARG	;;
			p)	prompt=$OPTARG	;;
			u)	user=$OPTARG	;;
		esac
	done

	if [[ -t 2 ]]; then
		{
		echo "Enter credentials for $prompt:"
		$nouser || {
			read -rp $'username: \001\e[1m\002' \
				-ei "$user" user
			printf '\e[m'
		}
		read -rp 'password: ' -es pass
		echo ""
		} </dev/tty >/dev/tty
		printf "$fmt" "$user" "$pass"
		return 0
	elif [[ $DISPLAY ]]; then
		zenity --forms \
		--title "Enter credentials" \
		--text "Enter credentials for $prompt:" \
		--add-entry "Username:" \
		--add-password "Password:" \
		--separator $'\n' | {
			read -r user &&
			read -r pass &&
			printf "$fmt" "$user" "$pass"
		}
	else
		echo >&2 "No credentials for $obj found."
		return 1
	fi
}

# getcred_var(host, [service], object, $uservar, $passvar)
# obtain credentials for service@host and put into given variables

getcred_var() {
	local OPT OPTARG
	local nouser=''
	while getopts 'U' OPT; do
		case $OPT in
			U)	nouser="-U"	;;
		esac
	done

	local host=$1 service=$2 obj=$3 uvar=${4:-user} pvar=${5:-pass}
	local fmt='%u%n%p' data= udata= pdata=
	local prompt="$obj on $host"
	if data=$(getnetrc_fqdn "$host" "$service" '%u%n%p'); then
		{ read -r udata; read -r pdata; } <<< "$data"
		declare -g "$uvar=$udata" "$pvar=$pdata"
	elif data=$(readcred $nouser -p "$prompt" -f '%s\n%s\n'); then
		{ read -r udata; read -r pdata; } <<< "$data"
		declare -g "$uvar=$udata" "$pvar=$pdata"
	else
		return 1
	fi
}

# getcred_samba(host, [service], objectname)
# obtain credentials for service@host, output in smbclient format

getcred_samba() {
	local host=$1 service=$2 obj=$3
	local fmt='username=%u%npassword=%p'
	local prompt="$obj on $host"
	getnetrc_fqdn "$host" "$service" "$fmt" ||
	readcred "$prompt"
}

# getnetrc_fqdn(host, [service], format)
# call getnetrc for [service@]host and [service@]fqdn until success

getnetrc_fqdn() {
	local host=$1 service=$2 fmt=$3
	local fqdn=$(fqdn "$host")
	getnetrc -df "$fmt" "$service@$host" ||
	{ [[ $host != $fqdn ]] &&
	getnetrc -df "$fmt" "$service@$fqdn"; }
}
