def filter_lines(input_file, keyword_file, output_file):
    with open(input_file, 'r') as input_f:
        with open(keyword_file, 'r') as keyword_f:
            keywords = keyword_f.read().splitlines()

        matching_lines = []
        for line in input_f:
            for keyword in keywords:
                if keyword in line:
                    matching_lines.append(line)
                    break

    with open(output_file, 'w') as output_f:
        output_f.writelines(matching_lines)

# Usage example
input_file = 'mobilenet_v2_192res_1.0_inat_bird_labels.txt'  # Path to the input file
keyword_file = 'californiabirds.txt'  # Path to the keyword file
output_file = 'includedbirds.txt'  # Path to the output file

filter_lines(input_file, keyword_file, output_file)