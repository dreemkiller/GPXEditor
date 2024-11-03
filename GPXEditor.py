import argparse
import datetime
import gpxpy
import gpxpy.gpx
from dataclasses import dataclass

@dataclass
class Adjustment:
    start: datetime.datetime
    end: datetime.datetime

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
def are_adjustments_consistent(adjustments):
    # first check - make sure each end is after its start
    for this_adjustment in adjustments:
        if this_adjustment.end < this_adjustment.start:
            print("Provided adjustment start:", this_adjustment.start, " occurs after corresponding adjustment end:", this_adjustment.end)
            return False
    # second check - make sure timespans don't overlap
    reference_index = 0
    for reference_adjustment in adjustments:
        comparison_index = 0
        for comparison_adjustment in adjustments:
            if reference_index != comparison_index: # don't want to compare a region to itself
                if reference_adjustment.start < comparison_adjustment.start and reference_adjustment.end > comparison_adjustment.start:
                    # comparison_start is inside reference region
                    return False
                if reference_adjustment.start < comparison_adjustment.end and reference_adjustment.end > comparison_adjustment.end:
                    # comparison_end is inside reference region
                    return False
                if reference_adjustment.start > comparison_adjustment.start and reference_adjustment.start < comparison_adjustment.end:
                    # reference_start is inside comparison region
                    return False
                if reference_adjustment.end > comparison_adjustment.start and reference_adjustment.end < comparison_adjustment.end:
                    # reference_end is inside comparison region
                    return False
            comparison_index += 1
        reference_index += 1
    # passed everything, must be good
    return True

def sort_adjustments(starts, ends):
    zipped = zip(starts, ends)
    zipsorted = sorted(zipped)
    sorted_adjustments = []
    for this_start, this_end in zipsorted:
        new_adjustment = Adjustment(this_start, this_end)
        sorted_adjustments.extend((new_adjustment,))
    return sorted_adjustments
    


def main():
    arg_parser = create_arg_parser()

    args = arg_parser.parse_args()
    adjustments = []
    if args.adjustment_start is not None:
        if type(args.adjustment_start) != type(args.adjustment_end) or len(args.adjustment_start) != len(args.adjustment_end):
            print("Each 'adjustment-start' argument must be paired with an 'adjustment-end' argument")
            arg_parser.print_help()
            exit(1)
    
        adjustments = sort_adjustments(args.adjustment_start, args.adjustment_end)
    

        if not are_adjustments_consistent(adjustments):
            print('Provided adjustment regions are not consistent. Either an end is before a start, or the adjustment regions overlap')
            arg_parser.print_help()
            exit(1)

    # Parsing an existing file:
    # -------------------------

    gpx_file = open(args.input, 'r')

    gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        one_second = datetime.timedelta(seconds=1)
        found_remove_before_time = False
        for segment in track.segments:
            current_point_index = 0
            for point in segment.points:
                if args.remove_before != None and point.time < args.remove_before:
                    segment.remove_point(0) # it's always zero, because we're removing from the beginning
                    current_point_index = current_point_index - 1 # now this number is negative, but will be incremented before being used again
                elif args.remove_before != None and point.time > args.remove_before and not found_remove_before_time:
                    # This is the first point that we've found with a time that's >= remove_before time - so remove_before occurred in a gap in the gpx timeline (probably because the rider was stopped).
                    # We need to fill that gap with the data from this point
                    found_remove_before_time = True
                    point_copy = point
                    point_copy.time = args.remove_before
                    while(point_copy.time < point.time):
                        segment.points.prepend(point_copy)
                        point_copy.adjust_time(datetime.tiledelta(seconds=1))
                    
                else: # if an adjustment occurs before args.remove_point, we will (rightly) ignore it. But why would someone do that? Maybe I should write a bug just to punish them
                    if len(adjustments) > 0:
                        for this_adjustment in adjustments:
                            adjustment_delta = this_adjustment.end - this_adjustment.start
                            if point.time > this_adjustment.start and point.time < this_adjustment.end:
                                print("Removing point at time ", point.time)
                                segment.remove_point(current_point_index)
                                current_point_index = current_point_index -1
                            if point.time >= this_adjustment.end:
                                print("Adjusting time of point at time:", point.time)
                                point.adjust_time(-adjustment_delta)
                current_point_index = current_point_index + 1

    output_gpx_file = open(args.output, 'w')
    output_gpx_file.write(gpx.to_xml())

if __name__ == "__main__":
    main()