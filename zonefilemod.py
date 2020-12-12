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

def __update_zonefile(zonefile_content, action_tuple):
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

def __print_arguments_help():
  print("No command line arguments provided")
  print("""
    -f    Filename to modify (must be ending with .zone)
    -v    Be verbose (show JSON dumps)
    -a    Append record (-a DNS_RECORD_CONTENT) NOT IMPLEMENTED
    -i    Insert record (-i DNS_RECORD_CONTENT) WORK IN PROGRESS
    -u    Update record (-u DNS_RECORD_CONTENT) NOT IMPLEMENTED
    -d    Delete record (-d DNS_RECORD_IDENT) WORK IN PROGRESS
    -s    Select record (-s DNS_RECORD_IDENT) NOT IMPLEMENTED

NOTE: I do not know yet the difference between Append and Insert.
I will need to define it yet. But the idea is to use Insert for
replacing if existing and Append to insert another one if existing.
Update then needs a scope argument like WHERE from SQL.
Most important ones are Insert and Delete, since I will need those.
  """)

def __interpret_arguments(arguments_list):
  interpreted_arguments_dict = {}
  interpreted_arguments_dict["verbose"] = False
  filename_follows = False
  record_follows = ""
  while len(arguments_list) > 0:
    current_argument = arguments_list.pop(0)
    if record_follows:
      interpreted_arguments_dict["record"].append( ( record_follows, current_argument ) )
      record_follows = ""
      continue
    if filename_follows:
      interpreted_arguments_dict["file"] = current_argument
      filename_follows = False
      continue
    if current_argument == "-f":
      filename_follows = True
      continue
    elif current_argument == "-v":
      interpreted_arguments_dict["verbose"] = True
      continue
    elif current_argument == "-s":
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = "select"
      continue
    elif current_argument == "-u":
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = "update"
      continue
    elif current_argument == "-a":
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = "append"
      continue
    elif current_argument == "-d":
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = "delete"
      continue
    elif current_argument == "-i":
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = "insert"
      continue
    else:
      if "unknown" not in interpreted_arguments_dict:
        interpreted_arguments_dict["unknown"] = []
      interpreted_arguments_dict["unknown"].append( current_argument )
  return interpreted_arguments_dict

def __get_zone_filename(interpreted_arguments):
  zone_filename = None
  if "file" in interpreted_arguments:
    possible_zone_filename = interpreted_arguments["file"]
    partitioned_zone_filename = str(possible_zone_filename).rpartition(".")
    if partitioned_zone_filename[1] and partitioned_zone_filename[2] == "zone":
      if os.path.exists(possible_zone_filename):
        if os.path.isfile(possible_zone_filename):
          zone_filename = os.path.abspath( possible_zone_filename )
  return zone_filename

def __read_zonefile_content(zone_filename):
  zonefile = open(zone_filename, "r")
  zone_content = zonefile.read()
  zonefile.close()
  return zone_content

if __name__ == "__main__":
  interpreted_arguments = None
  command_line_arguments = sys.argv[1:]
  if command_line_arguments:
    interpreted_arguments = __interpret_arguments(command_line_arguments)
  else:
    __print_arguments_help()
    sys.exit(1)
  zone_filename = __get_zone_filename( interpreted_arguments )
  if interpreted_arguments["verbose"]:
    print(json.dumps(interpreted_arguments, indent=2))
    if zone_filename is not None:
      print("Found filename: " + zone_filename)
  if zone_filename is not None:
    original_zone_content = __read_zonefile_content(zone_filename)
    updated_zone_content = __update_zonefile(original_zone_content, None)
