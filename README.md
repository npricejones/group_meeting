# Group Meeting Assignment Code

## Description
This code schedules a group of people for presenting and taking notes in a group meeting. 

Note that the default date format for all actions described below is `YYYY-MM-DD`

## Getting Started

Clone this repository into the desired working directory. 

Open `example_person.txt`, and save it with a name relevant to someone in your group (keeping the `.txt` extension). Fill in their `NAME`, the first date they will be available to participate (`START`), and the last date they will be available (`END`). By default, the program assumes that each person will both take `NOTES` and `TALK`, but set these to `False` if this is note the case. Finally, if there are dates that this person cannot (`FORBID`) or *must* present (`FORCE`), list those dates in the appropriate row, comma-separating for multiple values.

Repeat this process for all group members.

Once all group members have configuration files, open `example_constraint.txt` and save it as `constraints.txt`. Fill in the first date meetings occur (`START`), the last date of meetings (`END`), and the day(s) of the week (`WEEK`) as a string or integer (list for multiple meetings per week). For example, if the weekday is Thursday, all of the following formats are equivalent: `Thursday`, `thursday`, `Thu`, `thu`, and `4`. List any dates on which meetings will not occur in the `FORBID` row, comma-separating for multiple values. Finally, list all of the participant files (without extension) in the `PEOPLE` row.

Once this set up is complete, do the following:

```
python assignment.py
```

The schedule will be printed to console and saved to a file called `schedule_<START>_<END>.txt`, where the text between the `<>` is replaced with your start and end dates.

## Command line arguments

This code supports command line arguments to specify meeting parameters. While `constraints.txt` is used as the default for scheduling, you can store constraints in files with names of your choosing (as long as they retain the format). The command line argument `-c` or `--cnstrt` allows you to specify the name of the constraint file you wish to use.

If used, the other arguments override the parameters given in the constraints file. In this way you can specify a new start date (`-s` or `--start`), a new end date (`-e`, `--end`), and a new weekday(s) for meetings (`-w`, `--week`).

An example of command line use might be:

```
python assignment.py -c summer_constraints.txt -w Friday
```