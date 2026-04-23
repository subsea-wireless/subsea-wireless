import sys
import csv
import json
from jsonschema import Draft7Validator
from tabulate import tabulate
from collections import Counter
import argparse

ID_UNASSIGNED = 255    # Set to a number that is within limits of JSON schema but not used (e.g. maximum value). Can be used to trigger automatic numbering

def main():
    rewrite_data = False    # Set to true if rewrite_ parameter specified and overwrite is required
    overall_pass = True

    parser = argparse.ArgumentParser(
        description="Validate a JSON file against a specified JSON schema and run custom tests."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the JSON data file to validate."
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Path to the JSON schema file to validate against."
    )
    parser.add_argument(
        "--proto",
        help="Path to the protobuf file to be generated from the parameters after successful validation"
    )
    parser.add_argument(
        "--immediate_exit",
        action="store_true",
        help="Exit on first failure, otherwise complete subsequent tests"
    )
    parser.add_argument(
        "--markdown_table",
        action="store_true",
        help="Generate a human readable version of the parameter list in github markdown format"
    )
    parser.add_argument(
        "--csv_file",
        help="Path to the CSV file to be generated from the parameters after successful validation"
    )
    parser.add_argument(
        "--rewrite_default_access",
        action="store_true",
        help="Rewrite the specified parameter file with default access added to any parameters where no access is specified"
    )
    parser.add_argument(
        "--rewrite_auto_number_id",
        action="store_true",
        help=F"Rewrite the specified parameter file with automatically assigned ID number for IDs currently set to {ID_UNASSIGNED}"
    )

    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            data = json.load(f)['all']
    except Exception as e:
        print(f"::error::Failed to load JSON file '{args.file}': {e}")
        sys.exit(1)

    try:
        with open(args.schema, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"::error::Failed to load JSON schema file '{args.schema}': {e}")
        sys.exit(1)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

    error_rows = []
    for e in errors:
        error_rows.append([
            '.'.join(str(x) for x in e.path) or 'root',
            e.message,
            repr(e.instance)
        ])

    print("\n### Schema Validation Results")
    if error_rows:
        print(tabulate(error_rows, headers=["Path", "Message", "Value"], tablefmt="github"))
        print(F"Schema validation failed: {args.file} is not valid against schema defined in {args.schema}")
        if args.immediate_exit:
            sys.exit(1)
        else:
            overall_pass = False
    else:
        print(F"✅ {args.file} validated against {args.schema}")

    # Custom tests
    custom_test_rows = []   # List of reports
    cleaned_data = [] # Store for clean subset of parameters to allow subsequent testing

    custom_pass = True

    # Per-parameter tests
    for param in data:
        if 'access' not in param:
            if args.rewrite_default_access:
                print(F"Adding default readonly access for {param['id']}:{param['description']}")
                param['access']={"dry": {"read": True}, "wet": {"read": True}}
                rewrite_data = True
            else:
                custom_test_rows.append([F"No access specified for parameter {param['id']}:{param['description']}", "FAIL"])

    # Parameter global tests
    # Check for duplicate IDs, rewrite if specified
    id_duplicates = []
    ids = []

    try:
        ids = [int(param['id']) for param in data]  # Schema guarantees all should be integers
    except:
        # Shouldn't get here without failure in schema validation, report and try to recover for subsequent tests
        custom_test_rows.append([F"Invalid ID in parameter, should result in schema fail above", "FAIL"])
        for param in data:
            if 'id' not in param or not isinstance(param['id'], int):
                custom_test_rows.append([F" -- Invalid ID in {param.get('id')}:{param.get('name')} ({param.get('description')})", "FAIL"])
            else:
                cleaned_data.append(param)
        ids = [int(param['id']) for param in cleaned_data]  # After cleaning, all will be present and integer
        custom_pass = False

    id_counts = Counter(ids)
    if args.rewrite_auto_number_id and ID_UNASSIGNED in id_counts.keys():
        del id_counts[ID_UNASSIGNED]    # Remove the placeholder from the list before getting the highest value
        last_id = max(id_counts.keys()) + 1
        print(F"\n### Auto-renumbering from {ID_UNASSIGNED} to new IDs starting at {last_id}")

        for param in data:
            if param['id'] == ID_UNASSIGNED:
                param['id'] = last_id
                last_id += 1
        rewrite_data = True

    id_duplicates = [id_ for id_, count in id_counts.items() if count > 1]
    for duplicate in id_duplicates:
        custom_test_rows.append([F"Duplicate ID {duplicate}", "FAIL"])
        custom_pass = False

    if custom_pass:
        custom_test_rows.append([F"Duplicate IDs", "PASS"])

    print("\n### Custom Tests")
    print(tabulate(custom_test_rows, headers=["Test", "Result"], tablefmt="github"))

    if any(row[1] == "FAIL" for row in custom_test_rows):
        if args.immediate_exit:
            sys.exit(1)
        else:
            print(F"Custom tests fail")
            overall_pass = False
    else:
        print(F"✅ Custom tests pass")

    if overall_pass:            
        ids = [int(param['id']) for param in data]  # All tests passed so all should be valid integers
        print(F"  - Parameters defined: {len(ids)}")
        print(F"  - Highest ID defined: {max(ids)} ")
    else:
        sys.exit(1)

    if rewrite_data:
        print(F"Overwriting {args.file}")
        with open(args.file, "w") as fp:
            json.dump({"all":data} , fp, indent = 4) 

    data.sort(key=lambda x: int(x['id'])) # Sort by integer ID before outputting other formats

# Generate protobuf
    if args.proto:
        proto_contents = """
// This file is auto-generated by the validation action when parameters are updated
// DO NOT EDIT IT MANUALLY
syntax = "proto3";
package subseawireless;
option java_package = "com.subseawireless.parameters";

message Parameter{
  enum identifier{
    INVALID = 0;
"""
        # proto3 requires enums to start at zero, but zero is not used as an ID for this standard
        for param in data:
            proto_contents += f'    {param["name"]} = {param["id"]};\n'

        proto_contents += """  }
  identifier id = 1;
  bool bool = 2;
  int32 integer = 3;
  string string = 32;
}

message Message{
  int32 source = 1;
  int32 target = 2;
  repeated int32 requests = 3;  // List of parameter IDs requested
  repeated Parameter parameters = 4; // List of parameters sent
  repeated Parameter responses = 5; // List of parameters sent as response
}
        """

        proto_file = open(args.proto, "w")
        proto_file.write(proto_contents)
        proto_file.close()
        print("\n### Protobuf")
        print(F"Generated {args.proto} from {args.file}")

# Generate human readable versions
    if args.markdown_table:
        table = []
        for p in data:
            table.append([
                p.get("id"), 
                p.get("name"), 
                p.get("description"),
                p.get("representation"),
                p.get("minimum", "—"),
                p.get("maximum", "—"),
                p.get("pattern", "—"),
                ", ".join(map(str, p.get("valid integers", []))) if "valid integers" in p else "—",
                ", ".join(p.get("valid strings", [])) if "valid strings" in p else "—",
                f'R: {p.get("access", {}).get("dry", {}).get("read", "—")}, '
                f'W: {p.get("access", {}).get("dry", {}).get("write", "—")}',
                f'R: {p.get("access", {}).get("wet", {}).get("read", "—")}, '
                f'W: {p.get("access", {}).get("wet", {}).get("write", "—")}',
                ", ".join(f"{k.capitalize()}: {v}" for k,v in p.get("optional", {}).items())
                if "optional" in p else "—"
            ])

        print(tabulate(table, headers=["ID","Name","Description","Representation","Min","Max",
                                    "Pattern","Valid Ints","Valid Strings",
                                    "Dry Access","Wet Access","Optionals"]))

    if args.csv_file:
        with open(args.csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "ID", "Name", "Description", "Representation", 
                "Min", "Max",
                "Pattern", "Valid Integers", "Valid Strings",
                "Dry Read", "Dry Write", "Wet Read", "Wet Write", 
                "Optionals"
            ])
            
            for p in data:
                access={"dry":{"read":"", "write":""}, "wet":{"read":"", "write":""}}
                for dir in ['read', 'write']:
                    for iface in ['dry', 'wet']:
                        if dir in p.get("access", {}).get(iface, {}) and p['access'][iface][dir]: # If present and set,  
                            if p['access']['dry'].get(F'{dir}_option', False):
                                access[iface][dir] += "Opt "
                            if p['access']['dry'].get(F'{dir}_auth', False):
                                access[iface][dir] += "Auth"
                            if len(access[iface][dir]) == 0:    # No Option or Auth
                                access[iface][dir] = "Yes"
                        else:
                            pass # access[iface][dir] = "None"
                writer.writerow([
                    p.get("id"),
                    p.get("name"),
                    p.get("description"),
                    p.get("representation"),
                    p.get("minimum", ""),
                    p.get("maximum", ""),
                    p.get("pattern", ""),
                    ",".join(map(str, p.get("valid integers", []))) if "valid integers" in p else "",
                    ",".join(p.get("valid strings", [])) if "valid strings" in p else "",
                    f'{access["dry"]["read"]}',
                    f'{access["dry"]["write"]}',
                    f'{access["wet"]["read"]}',
                    f'{access["wet"]["write"]}',
                    ", ".join(f"{k.capitalize()} " for k,v in p.get("optional", {}).items()) if "optional" in p else ""
                ])
        if args.csv_file:
            print("\n### CSV File")
            print(F"Generated {args.csv_file} from {args.file}")


if __name__ == "__main__":
    main()
