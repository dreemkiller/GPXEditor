import argparse
import datetime
import gpxpy
import gpxpy.gpx


def convert_to_datetime(s):
    # add a UTC timezone offset to the end of the time
    tz_s = s + " +0000"
    ret = datetime.datetime.strptime(tz_s, "%Y-%m-%d %H:%M:%S %z")
    return ret

def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--input',
        type=str,
        required=True,
    )
    parser.add_argument(
        '-o',
        '--output',
        type=str,
        required=True,
    )
    parser.add_argument(
        '-b',
        '--remove-before',
        type=convert_to_datetime,
    )
    parser.add_argument(
        '-s',
        '--adjustment-start',
        type=convert_to_datetime,
        action='append',
    )
    parser.add_argument(
        '-e',
        '--adjustment-end',
        type=convert_to_datetime,
        action='append',
    )
    return parser

# determine if the provided starts/ends are consistent:
#   1. is each end later than it's corresponding start?
#   2. If the timespans of the adjustments overlap, that is bad
def are_adjustments_consistent(starts, ends):
    # first check - make sure each end is after its start
    for this_start, this_end in zip(starts, ends):
        if this_end < this_start:
            print("Provided adjustment start:", this_start, " occurs after corresponding adjustment end:", this_end)
            return False
    # second check - make sure timespans don't overlap
    reference_index = 0
    for reference_start, reference_end in zip(starts, ends):
        comparison_index = 0
        for comparison_start, comparison_end in zip(starts, ends):
            if reference_index != comparison_index: # don't want to compare a region to itself
                if reference_start < comparison_start and reference_end > comparison_start:
                    # comparison_start is inside reference region
                    return False
                if reference_start < comparison_end and reference_end > comparison_end:
                    # comparison_end is inside reference region
                    return False
                if reference_start > comparison_start and reference_start < comparison_end:
                    # reference_start is inside comparison region
                    return False
                if reference_end > comparison_start and reference_end < comparison_end:
                    # reference_end is inside comparison region
                    return False
            comparison_index += 1
        reference_index += 1
    # passed everything, must be good
    return True

def main():
    arg_parser = create_arg_parser()

    args = arg_parser.parse_args()

    print(args.remove_before)
    print('start:', args.adjustment_start)
    print('end:', args.adjustment_end)
    if type(args.adjustment_start) != type(args.adjustment_end) or len(args.adjustment_start) != len(args.adjustment_end):
        print("Each 'adjustment-start' argument must be paired with an 'adjustment-end' argument")
        arg_parser.print_help()
        exit(1)

    if not are_adjustments_consistent(args.adjustment_start, args.adjustment_end):
        print('Provided adjustment regions are not consistent. Either an end is before a start, or the adjustment regions overlap')
        arg_parser.print_help()
        exit(1)

    # Parsing an existing file:
    # -------------------------

    gpx_file = open(args.input, 'r')

    gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        one_second = datetime.timedelta(seconds=1)
        for segment in track.segments:
            current_point_index = 0
            for point in segment.points:
                if args.remove_before != None and point.time < args.remove_before:
                    segment.remove_point(0) # it's always zero, because we're removing from the beginning
                    current_point_index = current_point_index - 1

                if len(args.adjustment_start) > 0:
                    for this_start, this_end in zip(args.adjustment_start, args.adjustment_end):
                        adjustment_delta = this_end - this_start
                        if point.time > this_start and point.time < this_end:
                            print("Removing point at time ", point.time)
                            segment.remove_point(current_point_index)
                            current_point_index = current_point_index -1
                        if point.time >= this_end:
                            point.adjust_time(-adjustment_delta)
                current_point_index = current_point_index + 1

    output_gpx_file = open(args.output, 'w')
    output_gpx_file.write(gpx.to_xml())

if __name__ == "__main__":
    main()