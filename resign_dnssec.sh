#!/bin/sh

zonefilesdir="/var/www/zonefiles"
autodnssecdir="${HOME}/software/autodnssec"
dnssecfilesdir="${HOME}/content/dnssec"

for i in "$zonefilesdir" "$autodnssecdir" "$dnssecfilesdir"
do \
  if [ ! -d "$i" ]
  then \
    echo "Path $i is not a directory, exitting."
    exit 1
  fi
done

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
