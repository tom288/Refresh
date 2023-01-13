"""
If the input VMF does not contain shuffled spawns then this will do nothing.
Otherwise this will write an unshuffled VMF to the output path.
Calling main does some filename work:
If the output path is not specified then the suffix .unshuffled is used.
If the output path is the input path then a temporary .unshuffled file is used,
and the old input file is renamed to .backup.
"""

# TODO Use argparse or similar to offer command line help and simplify main

import os
import re
import sys

# Define which entity properties we are interested in and record their indices
CLASSNAME, TARGETNAME, PROP_COUNT = range(3)
PROPS = [None] * PROP_COUNT
PROPS[CLASSNAME] = "classname"
PROPS[TARGETNAME] = "targetname"

# Returns True if this writes to output_path, otherwise False
def unshuffle(input_path, output_path):
    # Make sure PROPS is correctly defined
    if None in PROPS:
        print("ERROR: Variable PROPS is not correctly defined")
        return False

    # Occurrences in the input file to record
    num_lines = 0
    num_entities = 0
    num_spawns = 0

    # Information about the named spawns to record
    named_spawn_targetnames = []
    line_to_targetname = {}
    targetname_to_text = {}

    # Collect information about various occurrences and the named spawns
    with open(input_path) as input_file:
        patterns = [re.compile("^\s*\"%s\"\s+\".*\"\s*$" % p) for p in PROPS]
        in_entity = False
        bracket_level = 0
        entity_props = [None] * PROP_COUNT
        entity_text = []
        entity_line = None
        for line in input_file:
            num_lines += 1
            if not in_entity and line.rstrip() == "entity":
                in_entity = True
                entity_line = num_lines
                bracket_level = 0
                num_entities += 1
            elif in_entity and line.strip() == "{":
                bracket_level += 1
            elif in_entity and line.strip() == "}":
                bracket_level -= 1
                if bracket_level <= 0 and in_entity:
                    if entity_props[CLASSNAME] == "info_player_teamspawn":
                        num_spawns += 1
                        if entity_props[TARGETNAME] is not None:
                            name = entity_props[TARGETNAME]
                            named_spawn_targetnames.append(name)
                            line_to_targetname[entity_line] = name
                            targetname_to_text[name] = entity_text
                    in_entity = False
                    entity_props = [None] * PROP_COUNT
                    entity_text = []
            elif bracket_level == 1:
                for i, pattern in enumerate(patterns):
                    if pattern.match(line):
                        prop = PROPS[i]
                        entity_props[i] = re.sub(
                            "\"%s\"" % prop,
                            "",
                            line
                        ).strip().strip("\"")
            if in_entity:
                entity_text.append(line)

    # Display occurrence information
    print("Parsed %d lines" % num_lines)
    print("Found %d entities" % num_entities)
    print("Found %d spawns" % num_spawns)
    print("Found %d named spawns" % len(named_spawn_targetnames))

    # Sort the information we have on named spawns
    def name_to_num(name):
        # The names can contain ints or floats but they must be at the end
        num = None
        for i in range(1, len(name) + 1):
            try: 
                num = float(name[-i:])
            except ValueError:
                break
        if num is not None:
            return num
        print("Ignored non-numeric name \"%s\"" % name)
        return float("inf")

    sorted_spawns = sorted(named_spawn_targetnames, key=name_to_num)

    # Check whether the spawns are actually shuffled to begin with
    shuffled = False
    for i, name in enumerate(named_spawn_targetnames):
        if name != sorted_spawns[i]:
            shuffled = True
            break
    if not shuffled:
        print("The named spawns are not shuffled so no work is necessary")
        return False

    num_lines = 0

    # # Unshuffle the named spawns
    with open(input_path) as input_file, open(output_path, "w") as output_file:
        skips = 0
        targetnames = 0
        for line in input_file:
            num_lines += 1
            if num_lines in line_to_targetname:
                skips = len(targetname_to_text[line_to_targetname[num_lines]])
                text = targetname_to_text[sorted_spawns[targetnames]]
                output_file.write("".join(text))
                targetnames += 1
            if skips > 0:
                skips -= 1
            else:
                output_file.write(line)

    print("Wrote %d lines to %s" % (num_lines, output_path))
    return True

def main():
    # Determine input and output paths
    if len(sys.argv) < 2:
        print("You must specify an input file")
        print("e.g. python %s <path_to_input_vmf> [output_path]" % sys.argv[0])
        return

    input_path = sys.argv[1]
    ext = input_path.split('.')[-1]
    if ext not in ["vmf", "vmx"]:
        print("You must provide a vmf or vmx file as input")
        return

    output_path = re.sub('.%s' % ext, '.unshuffled.%s' % ext, input_path)
    out_equals_in = False
    if len(sys.argv) > 2:
        if input_path != sys.argv[2]:
            output_path = sys.argv[2]
        else:
            out_equals_in = True
    
    # Unshuffle
    wrote = unshuffle(input_path, output_path)
    
    if out_equals_in and wrote:
        backup_path = re.sub('.%s' % ext, '.backup.%s' % ext, input_path)
        if os.path.isfile(backup_path):
            should_delete = None
            while should_delete not in ['y', 'n']:
                should_delete = input(
                    'About to delete pre-existing file %s - continue? (y/n) ' %
                    backup_path
                ).strip().lower()
            if should_delete == 'n':
                return
            os.remove(backup_path)
        os.rename(input_path, backup_path)
        print("Moved %s -> %s" % (input_path, backup_path))
        os.rename(output_path, input_path)
        print("Moved %s -> %s" % (output_path, input_path))

if __name__ == "__main__":
    main()
