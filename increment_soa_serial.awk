{
  soaposition = index($0, "SOA");
  if ( soaposition > 0 ) {
    match($0, /[0-9]{8,10}/);
    print substr($0, 0, RSTART - 1) "found!" substr($0, RSTART + RLENGTH );
  } else {
    print $0
  }
}