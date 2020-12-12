#!/usr/bin/env python3

import sys
import os
import time
import datetime
import re
import json

def __increment_soa(current_soa):
  current_formatted_date = datetime.datetime.now().strftime("%F")
  starting_soa = int( str.join("", current_formatted_date.split("-")) + "00" )
  current_soa = int( current_soa )
  if current_soa < starting_soa:
    return starting_soa
  else:
    return ( current_soa + 1 )
  return None

def __analyze_soa_rec(record_content):
  result_list = []
  record_parts_list = record_content.partition(";")
  record_part_line_counter = 0
  for record_part_line in record_parts_list[0].split("\n"):
    if record_part_line_counter > 0:
      result_list.append( ( "\n", True ) )
    result_list.append( ( record_part_line, True ) )
    record_part_line_counter += 1
  if record_parts_list[1]:
    record_comment_part = record_parts_list[2].partition("\n")
    result_list.append( ( record_parts_list[1] + record_comment_part[0], False ) )
    if record_comment_part[1]:
      result_list.append( ( record_comment_part[1], True ) )
    if record_comment_part[2]:
      result_list += __analyze_soa_rec(record_comment_part[2])
  return result_list

def __increment_soa_of_record(current_soa_record):
  num_val_re = re.compile("\d+")
  in_brackets = False
  incremented_soa = False
  new_soa_record_list = []
  new_soa_record_output = ""
  for soa_record_part in __analyze_soa_rec(current_soa_record):
    new_soa_record_part = soa_record_part
    if type(soa_record_part) is tuple and len(soa_record_part) == 2:
      if type(soa_record_part[1]) is bool:
        if soa_record_part[1]:
          record_part_content = soa_record_part[0]
          open_bracket_position = record_part_content.find("(")
          closing_bracket_position = record_part_content.find(")")
          if open_bracket_position > -1:
            in_brackets = True
          if in_brackets and not incremented_soa:
            found_num_val_search = None
            if open_bracket_position > 0:
              found_num_val_search = num_val_re.search(record_part_content, open_bracket_position)
            else:
              found_num_val_search = num_val_re.search(record_part_content)
            if found_num_val_search is not None:
              num_val_span = found_num_val_search.span()
              if type(num_val_span) is tuple and len(num_val_span) == 2:
                new_soa_serial = None
                content_before_serial = record_part_content[:num_val_span[0]]
                content_after_serial  = record_part_content[num_val_span[1]:]
                soa_serial = record_part_content[num_val_span[0]:num_val_span[1]]
                if soa_serial.isnumeric():
                  new_soa_serial = __increment_soa(soa_serial)
                  incremented_soa = True
                new_record_part_content = content_before_serial + str(new_soa_serial) + content_after_serial
                new_soa_record_part = ( new_record_part_content, soa_record_part[1] )
          if closing_bracket_position > -1:
            in_brackets = False
    new_soa_record_list.append(new_soa_record_part)
  for soa_record_part in new_soa_record_list:
    if type(soa_record_part) is tuple and len(soa_record_part) == 2:
      if type(soa_record_part[1]) is bool:
        new_soa_record_output += soa_record_part[0]
  return new_soa_record_output

def __incr_soa_of_zonefile(zonefile_content):
  zonefile_records_list = []
  new_zonefile_content = ""
  is_whitespace = re.compile("\s")
  for zonefile_line in zonefile_content.split("\n"):
    if not zonefile_line:
      if len(zonefile_records_list) > 0:
        zonefile_records_list_last_record = zonefile_records_list.pop()
        if not zonefile_records_list_last_record.endswith("\n\n"):
          zonefile_records_list_last_record += "\n"
        zonefile_records_list.append(zonefile_records_list_last_record)
      continue
    if is_whitespace.match(zonefile_line[0]):
      if len(zonefile_records_list) > 0:
        zonefile_records_list_last_record = zonefile_records_list.pop()
        zonefile_records_list_last_record += "\n" + zonefile_line
        zonefile_records_list.append(zonefile_records_list_last_record)
      else:
        zonefile_records_list.append(zonefile_line)
    else:
      zonefile_records_list.append(zonefile_line)
  for zonefile_record in zonefile_records_list:
    zonefile_record_parts_list = zonefile_record.split()
    following_typedef = False
    found_soa_record = False
    for zonefile_record_part in zonefile_record_parts_list:
      if zonefile_record_part == "IN":
        following_typedef = True
        continue
      if following_typedef:
        if zonefile_record_part == "SOA":
          found_soa_record = True
      following_typedef = False
    if new_zonefile_content:
      new_zonefile_content += "\n"
    if found_soa_record:
      new_zonefile_content += __increment_soa_of_record(zonefile_record)
    else:
      new_zonefile_content += zonefile_record
  return new_zonefile_content

if __name__ == "__main__":
  zonefile = open("/tmp/zonetest.txt", "r")
  zonefile_content = zonefile.read()
  new_zonefile_content = __incr_soa_of_zonefile(zonefile_content)
  zonefile.close()
  print("OLD:")
  print(zonefile_content)
  print("NEW:")
  print(new_zonefile_content)
