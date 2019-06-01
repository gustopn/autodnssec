#!/bin/sh -x

zonefilesdir=""
dnssecfilesdir=""

while [ $# -ge 1 ]
do \
  case "$1" in
    "-z") shift
          if [ $# -ge 1 ]
          then \
            zonefilesdir="$1"
          else \
            break
          fi ;;
    "-d") shift 
          if [ $# -ge 1 ]
          then \
            dnssecfilesdir="$1"
          else \
            break
          fi ;;
  esac
  shift
done

for i in "$zonefilesdir" "$dnssecfilesdir"
do \
  if [ ! -d "$i" ]
  then \
    echo "Path $i is not a directory, exitting."
    exit 1
  fi
done

for i in "$zonefilesdir"/*.zone
do \
  zoneidentifiername=`echo $i | awk -F'/' '{print $NF}'`
  zoneidentifiername="${zoneidentifiername%.zone}"
  for j in "${dnssecfilesdir}/K${zoneidentifiername}"*".key"
    do \
      if grep '(ksk)' "$j" >/dev/null
      then \
        KSK="${j%.key}"
      fi
      if grep '(zsk)' "$j" >/dev/null
      then \
        ZSK="${j%.key}"
      fi
    done
  ldns-signzone -n -s `openssl rand -hex 8 | tr -d "\n"` $i $ZSK $KSK
  unset ZSK
  unset KSK
done
