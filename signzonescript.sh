if [ -z "$1" ]
then \
  echo "Error: You have to provide key directory as first argument, none provided, giving up!"
  exit 1
fi

if [ ! -d "$1" ]
then \
  echo "Error: You have to provide key directory as first argument, no directory provided, giving up!"
  exit 2
fi

for i in *.zone
do \
  for j in "$1"/K"${i%.zone}"*
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