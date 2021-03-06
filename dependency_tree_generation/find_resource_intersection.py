from argparse import ArgumentParser

import common_module
import simplejson as json
import numpy
import os

PARAMS = 'params'
RESPONSE = 'response'
REQUEST = 'request'
URL = 'url'
METHOD = 'method'

def main(root_dir, num_iterations, pages, output_dir):
    common_module.create_directory_if_not_exists(output_dir)
    averages = []
    for page in pages:
        page = common_module.escape_url(page)
        print 'Processing ' + page

        skip_page = False # Indicator to decide whether to skip processing this page.
        page_common_resources = []
        total_resources = []
        for i in range(0, num_iterations):
            run_path = os.path.join(root_dir, str(i), page)
            network_filename = os.path.join(run_path, 'network_' + page)
            if not os.path.exists(network_filename):
                skip_page = True
                break
            resources = find_all_resources(network_filename, page)
            total_resources.append(len(resources))
            if len(page_common_resources) == 0:
                page_common_resources = resources
            else:
                page_common_resources = find_resource_intersection(page_common_resources, resources)
        output(output_dir, page, page_common_resources, args.output_to_stdout)

        if args.print_fraction:
            fraction = print_fraction(len(page_common_resources), total_resources, num_iterations)
            if fraction > 0:
                averages.append((page, fraction))

    if args.print_fraction:
        print 'average: ' + str(numpy.average([ x[1] for x in averages ]))

    if args.output_fraction_list:
        output_fraction_list(output_dir, averages)

def print_fraction(num_intersection, total_resources_count, num_iterations):
    running_sum = 0.0
    for i, resource_count in enumerate(total_resources_count):
        if resource_count != 0:
            fraction = 1.0 * num_intersection / resource_count
            running_sum += fraction
            print '\titeration: {0} total resources: {1} fraction: {2}'.format(i, resource_count, fraction)
    print '\taverage: {0}'.format((running_sum / num_iterations))
    return running_sum / num_iterations

def output_fraction_list(output_dir, averages):
    output_filename = os.path.join(output_dir, 'fraction.txt')
    sorted_averages = sorted(averages, key=lambda x: x[1])
    with open(output_filename, 'wb') as output_file:
        for average in sorted_averages:
            output_file.write('{0} {1}\n'.format(average[0], average[1]))

def output(output_dir, page, page_common_resources, to_stdout=True):
    if to_stdout:
        for resource in page_common_resources:
            print resource
    else:
        page_filename = os.path.join(output_dir, page)
        with open(page_filename, 'wb') as output_file:
            for resource in page_common_resources:
                output_file.write(resource + '\n')
            
def find_resource_intersection(first_resources, second_resources):
    return [ x for x in first_resources if x in second_resources ]

def find_all_resources(network_filename, page):
    resource_list = list()
    with open(network_filename, 'rb') as input_file:
        found_first_request = False
        for raw_line in input_file:
            network_event = json.loads(json.loads(raw_line.strip()))
            if not found_first_request and \
                network_event[METHOD] == 'Network.requestWillBeSent':
                if common_module.escape_url(network_event[PARAMS][REQUEST]['url']) \
                    == page:
                    found_first_request = True
            if not found_first_request:
                continue
            if network_event[METHOD] == 'Network.responseReceived':
                url = network_event[PARAMS][RESPONSE][URL]
                if url.startswith('http') and url not in resource_list:
                    resource_list.append(url)
    return resource_list

def get_pages(pages_file):
    '''
    Returns a list of page names.
    '''
    result = []
    with open(pages_file, 'rb') as input_file:
        for raw_line in input_file:
            if not raw_line.startswith("#"):
                line = raw_line.strip().split()
                page = common_module.escape_url(line[len(line) - 1])
                result.append(page)
    return result

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    parser.add_argument('pages_file')
    parser.add_argument('num_iterations', type=int)
    parser.add_argument('output_dir')
    parser.add_argument('--print-fraction', default=False, action='store_true')
    parser.add_argument('--output-to-stdout', default=False, action='store_true')
    parser.add_argument('--output-fraction-list', default=False, action='store_true')
    args = parser.parse_args()
    pages = get_pages(args.pages_file)
    main(args.root_dir, args.num_iterations, pages, args.output_dir)
