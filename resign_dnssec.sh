#!/bin/sh -x

# check with whereis for dirname and realpath
dirnamepath=`whereis -b dirname | awk '{print $2}'`
realpathpath=`whereis -b realpath | awk '{print $2}'`

# location of zone files (default: ${HOME}/work/zonefiles )
zonefilesdir="${HOME}/work/zonefiles"
# this project directory (default: this directory)
autodnssecdir=""
if [ -x "$dirnamepath" ] && [ -x "$realpathpath" ]
then \
  realpathcurrentscript=`realpath $0`
  autodnssecdir=`dirname $realpathcurrentscript`
fi
# location of dnssec keys (default: ${HOME}/work/dnssec)
dnssecfilesdir="${HOME}/work/dnssec"

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
    "-a") shift
          if [ $# -ge 1 ]
          then \
            autodnssecdir="$1"
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