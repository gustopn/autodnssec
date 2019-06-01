#!/bin/sh -x

# location of zone files (default: /home/{user}/work/zonefiles )
zonefilesdir="${HOME}/work/zonefiles"
# this project directory (default: this directory)
autodnssecdir="$(dirname $0)"
# location of dnssec keys (default: /home/{user}/work/dnssec)
dnssecfilesdir="${HOME}/work/dnssec"

while [ $# -ge 1 ]
do \
  case "$1" in
    "-z") shift
          zonefilesdir="$1" ;;
    "-a") shift 
          autodnssecdir="$1" ;;
    "-d") shift 
          dnssecfilesdir="$1" ;;
  esac
  shift
done

testifdirs() {
  for i in "$zonefilesdir" "$autodnssecdir" "$dnssecfilesdir"
  do \
    if [ ! -d "$i" ]
    then \
      echo "Path $i is not a directory, exitting."
      exit 1
    fi
  done
}

alltherest() {
  if cd "$zonefilesdir"
  then \
    for i in *.zone
    do \
      newfilecontent="$(cat "$i" | gawk -f "$autodnssecdir"/"increment_soa_serial.awk")"
      if [ -n "$newfilecontent" ]
      then \
        echo "$newfilecontent" | diff -w "$i" - | patch --quiet "$i"
      else \
        echo "Failed to increment SOA serial, exitting."
        exit 1
      fi
    done
    "${autodnssecdir}/signzonescript.sh" "$dnssecfilesdir"
    svn --quiet commit -m `date +%F` &&  svn --quiet up && svn diff -r PREV --diff-cmd diff -x -w
  fi
}