{
  soaposition = index($0, "SOA");
  if ( soaposition > 0 ) {
    match($0, /[0-9]{8,10}/);
    if ( soaposition > RSTART ) {
      print $0;
    }
    else
    {
      newserial = int(substr($0, RSTART, RLENGTH)) + 1;
      print substr($0, 0, RSTART - 1) newserial substr($0, RSTART + RLENGTH );
    }
  } else {
    print $0
  }
}