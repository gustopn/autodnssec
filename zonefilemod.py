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
    zone_record_ident = zonefile_record_parts_list[0]
    action_tuple_ident = None
    if type(action_tuple) is tuple:
      if action_tuple[0] in [ "append", "insert", "update" ]:
        action_tuple_ident = action_tuple[1].split()
        if len(action_tuple_ident) > 0:
          action_tuple_ident = action_tuple_ident[0]
        else:
          action_tuple_ident = None
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
      if action_tuple[0] == "delete" and zone_record_ident == action_tuple[1]:
        print("-------------- Deleting record: --------------")
        print( zonefile_record )
        print("-------------- End of deleted record. --------------\n")
      elif action_tuple[0] == "select" and zone_record_ident == action_tuple[1]:
        print("-------------- Selected record: --------------")
        print( zonefile_record )
        print("-------------- End of selected record. --------------\n")
        new_zonefile_content += zonefile_record
      elif action_tuple[0] == "insert" and zone_record_ident == action_tuple_ident:
        print("-------------- Overwriting record: --------------")
        print( zonefile_record )
        print("-------------- End of overwritten record. --------------\n")
      else:
        new_zonefile_content += zonefile_record
  if action_tuple[0] in [ "insert", "append" ]:
    print("-------------- Adding record: --------------")
    print( action_tuple[1] )
    print("-------------- End of added record. --------------\n")
    new_zonefile_content += action_tuple[1] + "\n"
  return new_zonefile_content

def __print_arguments_help():
  print("No command line arguments provided")
  print("""
    -f    Filename to modify (must be ending with .zone)
    -v    Be verbose (show JSON dumps)
    -a    Append record (-a DNS_RECORD_CONTENT)
    -i    Insert record (-i DNS_RECORD_CONTENT)
    -u    Update record (-u DNS_RECORD_CONTENT) NOT IMPLEMENTED
    -d    Delete record (-d DNS_RECORD_IDENT)
    -s    Select record (-s DNS_RECORD_IDENT)

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
  record_argument_map = {
    "-s": "select",
    "-i": "insert",
    "-a": "append",
    "-d": "delete",
    "-u": "update"
  }
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
    elif current_argument in [ "-s", "-u", "-a", "-d", "-i" ]:
      if "record" not in interpreted_arguments_dict:
        interpreted_arguments_dict["record"] = []
      record_follows = record_argument_map[current_argument]
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

def __write_zonefile_content(zone_filename, updated_zone_content):
  zonefile = open(zone_filename, "w")
  zonefile.write(updated_zone_content)
  zonefile.close()
  return None

def __validate_home_dir():
  home_dir = os.environ["HOME"]
  home_dir = os.path.abspath(home_dir)
  if os.path.exists(home_dir) and os.path.isdir(home_dir):
    if home_dir[0] == "/":
      home_dir_parts_list = home_dir[1:].split("/")
      home_dir_first_part = home_dir_parts_list.pop(0)
      if home_dir_first_part == "usr":
        if home_dir_parts_list.pop(0) == "home":
          return home_dir
      if home_dir_first_part == "home":
        return home_dir
  return None

def __read_config_file(config_file_path):
  config_file = open(config_file_path, "r")
  config_object = json.loads( config_file.read() )
  config_file.close()
  return config_object

def __create_config_file(config_file_path):
  config_object = {}
  if sys.stdout.isatty():
    print("You do not seem to have a config file, do you want to create one? (Y)")
    print("Would create a config file in: " + config_file_path)
    answer = input("Your Answer: ")
    if answer != "Y":
      return None
    zone_files_dir = input("OK, where do I find zone files? Path, please: ")
    if not os.path.isdir(zone_files_dir) or not os.path.exists(zone_files_dir):
      print("Wrong answer, skipping")
      return None
    dnssec_keys_dir = input("Well, we also need dnssec keys. Path, please: ")
    if not os.path.isdir(dnssec_keys_dir) or not os.path.exists(dnssec_keys_dir):
      print("Wrong answer, skipping")
      return None
    config_object["zones"]  = os.path.abspath(zone_files_dir)
    config_object["dnssec"] = os.path.abspath(dnssec_keys_dir)
    config_file = open(config_file_path, "w")
    config_file.write( json.dumps(config_object, indent=2) )
    config_file.close()
    return config_object
  return None

def __get_zone_file_paths_from_dir(dirinstance, dircounter):
  if not dircounter > 0:
    return None
  zonesfilepath_list = []
  with os.scandir(dirinstance) as dircontent:
    for dircontentinstance in dircontent:
      if dircontentinstance.is_dir():
        new_zone_file_paths = __get_zone_file_paths_from_dir(dircontentinstance.path, dircounter - 1)
        if new_zone_file_paths is not None and type(new_zone_file_paths) is list:
          zonesfilepath_list += new_zone_file_paths
      if dircontentinstance.is_file():
        if "zone" == dircontentinstance.name.rpartition(".")[2]:
          zonesfilepath_list.append( dircontentinstance.path )
  if len(zonesfilepath_list) > 0:
    return zonesfilepath_list
  return None

def __find_all_zone_files(config_params):
  if "zones" not in config_params:
    return None
  zonesdir = config_params["zones"]
  if os.path.exists(zonesdir) and os.path.isdir(zonesdir):
    return __get_zone_file_paths_from_dir(zonesdir, 2)
  return None

def __find_dnssec_key_for_domain(domain):
  if "zones" not in config_params or "dnssec" not in config_params:
    return None
  zonesdir  = config_params["zones"]
  dnssecdir = config_params["dnssec"]

if __name__ == "__main__":
  interpreted_arguments = None
  action_tuple_list = None
  original_zone_content = None
  updated_zone_content = None
  config_params = None
  home_dir = __validate_home_dir()
  config_file = ".dnszonefilemod.conf"
  config_file_path = None
  if home_dir is not None:
    config_file_path = str.join("/", [ home_dir, config_file ] )
    if os.path.exists(config_file_path):
      if os.path.isfile(config_file_path):
        config_params = __read_config_file(config_file_path)
    else:
      config_params = __create_config_file(config_file_path)
  if config_params is not None:
    print("Found config file with configuration:")
    print( json.dumps( config_params, indent=2 ) )
    print( json.dumps( __find_all_zone_files(config_params), indent=2) )
  command_line_arguments = sys.argv[1:]
  if command_line_arguments:
    interpreted_arguments = __interpret_arguments(command_line_arguments)
  else:
    __print_arguments_help()
    sys.exit(1) # TODO: Here this will be a problem soon!
  zone_filename = __get_zone_filename( interpreted_arguments )
  if interpreted_arguments["verbose"]:
    print(json.dumps(interpreted_arguments, indent=2))
    if zone_filename is not None:
      print("Found filename: " + zone_filename)
  if "record" in interpreted_arguments:
    action_tuple_list = interpreted_arguments["record"]
  if zone_filename is not None:
    original_zone_content = __read_zonefile_content(zone_filename)
    if action_tuple_list is not None and type(action_tuple_list) is list:
      current_zone_content = original_zone_content
      for action_tuple in action_tuple_list:
        current_zone_content = __update_zonefile(current_zone_content, action_tuple)
      updated_zone_content = current_zone_content
    else:
      updated_zone_content = __update_zonefile(original_zone_content, None)
  if interpreted_arguments["verbose"]:
    print("ORIGINAL:")
    print(original_zone_content)
    print("UPDATED:")
    print(updated_zone_content)
  if zone_filename is not None:
    current_timestamp = datetime.datetime.now().strftime("%s")
    backup_zone_filename = zone_filename + "-" + str( current_timestamp )
    if not os.path.exists( backup_zone_filename ):
      __write_zonefile_content( backup_zone_filename, original_zone_content )
      __write_zonefile_content( zone_filename, updated_zone_content )
