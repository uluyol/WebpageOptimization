import argparse
import dpkt
import os

HTTP_PREFIX = 'http://'
INTERVAL_SIZE = 10

def parse_file(trace_filename, page_load_intervals, output_directory):
    with open(trace_filename) as pcap_file:
        pcap_objects = dpkt.pcap.Reader(pcap_file)
        current_diff = -1
        bytes_received_per_interval = []
        current_interval_index = 0
        current_page_load_interval = page_load_intervals[current_interval_index]
        current_output_filename = os.path.join(output_directory, current_page_load_interval[0][len(HTTP_PREFIX):])
        current_output_file = open(current_output_filename, 'wb')
        first_ts = current_page_load_interval[1][0]
        print 'page: ' + current_page_load_interval[0]
        for ts, buf in pcap_objects:
            ts = ts * 1000
            if ts > current_page_load_interval[1][1]:
                # First, output to the file.
                print 'result len: ' + str(len(bytes_received_per_interval))
                output_to_file(bytes_received_per_interval, current_output_file)

                # The current timestamp is already greater than the end of the current interval
                # Get a new interval
                current_interval_index += 1
                if current_interval_index >= len(page_load_intervals):
                    break
                current_page_load_interval = page_load_intervals[current_interval_index]
                current_output_filename = os.path.join(output_directory, current_page_load_interval[0][len(HTTP_PREFIX):])
                current_output_file = open(current_output_filename, 'wb')
                first_ts = current_page_load_interval[1][0]
                current_diff = -1
                bytes_received_per_interval = []
                print 'page: ' + current_page_load_interval[0]

            if not current_page_load_interval[1][0] <= ts <= current_page_load_interval[1][1]:
                # The current timestamp is not in the page interval.
                continue


            eth = dpkt.ethernet.Ethernet(buf)
            if eth.type != dpkt.ethernet.ETH_TYPE_IP:
                # Only use IP packets 
                continue

            ip = eth.data
            tcp = ip.data
            if int(ip.p) != int(dpkt.ip.IP_PROTO_TCP) or (tcp.sport != 443 and tcp.sport != 80):
                # We only care about HTTP or HTTPS
                continue
            #print 'diff: ' + str(int(ts - first_ts)) + ' ts: ' + str(ts) + ' first_ts: ' + str(first_ts)
            current_diff = int(ts - first_ts) / INTERVAL_SIZE # diff 
            #print 'Current Diff: ' + str(current_diff)
            while len(bytes_received_per_interval) < current_diff:
                bytes_received_per_interval.append(0)
            if len(bytes_received_per_interval) == current_diff:
                # There isn't a bucket for this interval yet.
                bytes_received_per_interval.append(0)
            bytes_received_per_interval[int(current_diff)] += ip.len
    print 'Done.'

def output_to_file(bytes_received_per_interval, output_file):
    counter = 0
    running_sum = 0
    for i in range(0, len(bytes_received_per_interval)):
        bytes_received = bytes_received_per_interval[i]  # 100ms per one slot
        running_sum += bytes_received
        utilization = convert_to_mbits(bytes_received) / 0.6 # each 100ms can handle 6mbps * 0.1(s/100ms) = 0.6 mbits
        # utilization = convert_to_mbits(bytes_received) # just the actual speed.
        line = str(i * INTERVAL_SIZE) + ' ' + str(utilization)
        output_file.write(line + '\n')
        running_sum = 0

def convert_to_mbits(byte):
    return 1.0 * (byte * 8) / 1048576

def get_page_load_intervals(page_load_interval_filename):
    result = dict()
    with open(page_load_interval_filename, 'rb') as input_file:
        for raw_line in input_file:
            line = raw_line.rstrip().split()
            page = line[0]
            start_time = int(line[1])
            end_time = int(line[2])
            result[page] = (start_time, end_time)
    sorted_result = sorted(result.items(), key=lambda x: x[1][0])
    return sorted_result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('trace_filename')
    parser.add_argument('page_load_interval_filename')
    parser.add_argument('output_directory')
    args = parser.parse_args()
    page_load_intervals = get_page_load_intervals(args.page_load_interval_filename)
    parse_file(args.trace_filename, page_load_intervals, args.output_directory)