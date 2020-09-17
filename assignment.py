"""
assignment.py assigns presenters and notetakers for group meetings.

Usage:
    assignment [-h] [-s START] [-e END] [-w WEEK] [-c CNSTRT]

Options:
    -h, --help                   Show this screen
    -s START --start START       Start date of meetings in YYYY-MM-DD. If set,
                                 overrides start date assigned in constraint
                                 file. [default: None]
    -e END --end END             End date of meetings in YYYY-MM-DD. If set,
                                 overrides end date assigned in constraint
                                 file. [default: None]
    -w WEEK --week WEEK          Weekday of meetings. If set, overrides weekday
                                 assigned in constraint file. [default: None]
    -c CONSTRT --cnstrt CONSTRT  Constraint file [default: constraints.txt]

Examples:
    python assignment.py -c summer_constraints.txt

Natalie Price-Jones, UofT, 2020
"""


# Add ability to accomodate different weekday frequency
from docopt import docopt
import warnings
import calendar as cl
import numpy as np
import datetime as dt
import copy

fullnames = np.array(list(cl.day_name))
abrnames = np.array(list(cl.day_abbr))

def value_dist(arr,value):
    """
    Calculate the number of entries between an entry and a specific value 
    in an array.

    arr:    numpy array
    value:  value that bounds the entry counting

    Returns an array containing the distance to nearest instance of the 
    chosen value.
    """
    mask_val = arr==value
    idx_val = np.flatnonzero(mask_val)
    idx_nval = np.flatnonzero(~mask_val)
    if arr[-1]!=value:
        idx_val = np.r_[idx_val,len(arr)]
    out = np.zeros(len(arr),dtype=int)
    idx = np.searchsorted(idx_val,idx_nval)
    out[~mask_val]=idx_val[idx]-idx_nval
    return out

def read_constraints(fname: str,sep='=',comment='#'):
    """
    Read a constraints file and convert its entries to a dictionary.

    Arguments:
    fname:   file name string

    Keyword arguments:
    sep:     Character that separates keyword and value
    comment: Comment character used in constraints file (default:'#')


    Returns a dictionary of constraint information.
    """
    with open(fname) as file:
        contents = file.readlines()
    params = {}
    for line in contents:
        # scrub newlines and then remove comments
        realtext = line.split('\n')[0].split(comment)[0]
        # for non-header lines, separate key and value
        if realtext != '':
            var = realtext.split(sep)
            params[var[0]]=var[1]
    return params

def read_datelist(datestr: str,meetdates: np.array,sep=',',datesep='-',rangechar='()',
                  rangesep='_'):
    """
    Separates a string list of dates into date objects, unpacking date ranges.
    Arguments
    datestr:    String with list of dates
    meetdates:  List of meetings given as dt.date objects

    Keyword arguments
    sep:        Character that separates entries in datestr (default:',')
    datesep:    Character that separates parts of a single date (default:'-')
    rangechar:  Characters that bound a date range (default:'()')
    rangesep:   Character that separates the bounds of a date range
                (default:'_')


    Returns list of date objects, with ranges presented as tuples.
    """
    dates = datestr.split(sep)
    datelist=[]
    for date in dates:
        try:
            if rangechar[0] in date:
                start = date.split(rangesep)[0].split(rangechar[0])[1]
                year,month,day = start.split(datesep)
                start = dt.date(int(year),int(month),int(day))
                end = date.split(rangesep)[1].split(rangechar[1])[0]
                year,month,day = end.split(datesep)
                end = dt.date(int(year),int(month),int(day))
                if start==end:
                    warnings.warn(f'start {start} == end {end} in date range')
                else:
                    intervalmeetings = meetdates[(meetdates>=start)&(meetdates<=end)]
                    datelist.append(intervalmeetings)
            else:
                year,month,day = date.split(datesep)
                datelist.append([dt.date(int(year),int(month),int(day))])
        except ValueError:
            warnings.warn(f'Invalid date format in {date}, skipping')
    datelist = [item for sublist in datelist for item in sublist]
    return np.array(datelist)

class participant(object):
    """
    Class to hold participant properties

    Last modified: Price-Jones, 2020
    Created: Price-Jones, 2020
    """
    def __init__(self,fname: str,ext='.txt', **kwargs):
        """
        Read in participant properties.

        Arguments
        fname:  Name of participant file

        Keyword arguments
        ext:    Participant file extension (default:'.txt')

        Additional keyword arguments are passed to read_constraints

        Returns None

        """
        fname = fname+ext
        details = read_constraints(fname,**kwargs)
        self.name = details['NAME']
        if self.name=='':
            warnings.warn(f'I got an empty name for {fname}, defaulting to file name.')
        self.notes = details['NOTES']
        if self.notes=='':
            warnings.warn(f'Assuming {self.name} can take notes')
            self.notes=True
        elif self.notes=='True':
            self.notes=True
        elif self.notes=='False':
            self.notes=False
        self.talk = details['TALK']
        if self.talk=='':
            warnings.warn(f'Assuming {self.name} can present')
            self.talk=True
        elif self.talk=='True':
            self.talk=True
        elif self.talk=='False':
            self.talk=False
        # add conversion for dates
        self.start = details['START']
        self.end = details['END']
        self.forbid = details['FORBID']
        self.force = details['FORCE']

class schedule(object):
    """
    Class to perform scheduling over a fixed date range.
    """
    def __init__(self,start: str,end: str,weekdays: list,forbid: str,
                 people_list: list,freq=1,seed=1,**kwargs):
        """
        Stores meta scheduling information.

        start:          start date of meetings
        end:            end date of meetings
        weekdays:       day(s) of the week to hold meetings
        forbid:         dates where meetings won't be held
        people_list:    list of attendee information filenames
        freq:           number of weeks between subsequent meetings
        seed:           random seed to ensure reproduciblity of the schedule
        """
        # Set initial dates
        self.start=start
        self.end=end
        self.weekdays = []
        # Create date objects for the weekdays of the meetings
        for day in weekdays:
            day = day.strip().capitalize()
            if isinstance(day,str):
                if day in fullnames:
                    match = np.where(fullnames==day)[0][0]
                    self.weekdays.append(match)
                elif day in abrnames:
                    match = np.where(fullnames==day)[0][0]
                    self.weekdays.append(match)
                else:
                    warnings.warn('Invalid meeting day given. \
                                   Assuming today is a meeting day.')
                    self.weekdays.append(dt.date.today().weekday())
            elif isinstance(day,(int,float)):
                self.weekdays.append(int(day))
            else:
                warnings.warn('Invalid meeting day type. \
                               Assuming today is a meeting day.')
                self.weekdays.append(dt.date.today().weekday())
        
        self.freq = freq
        # Get all valid meeting days
        meetdates = self.get_meetdates()
        # Get forbidden meeting days (even if forbid is just range)
        self.forbid=read_datelist(forbid,meetdates,**kwargs)
        self.meetdates = meetdates[np.invert(np.in1d(meetdates,self.forbid))]
        self.people_list = people_list
        self.seed=seed
        # Get participants and their constraints
        self.people = {}
        self.names = []
        self.npresenters=0
        self.nnoters=0
        for p,person in enumerate(self.people_list):
            particip=participant(person)
            self.people[person]=particip
            self.names.append(particip.name)
            if particip.talk:
                self.npresenters+=1
            if particip.notes:
                self.nnoters+=1
        self.names=np.array(self.names)


    def get_meetdates(self,start=None,end=None,weekdays=None,freq=None,datesep='-'):
        """
        Calculate meeting dates.

        start:          start date of meetings
        end:            end date of meetings
        weekdays:       day(s) of the week to hold meetings
        freq:           number of weeks between subsequent meetings
        datesep:        separater in the datestring

        Returns list of valid date objects for meetings.

        """
        # If start, end, weekdays, or freq unspecified, use defaults from class
        if not start:
            start = self.start
            year,month,day = start.split(datesep)
            start = dt.date(int(year),int(month),int(day))
        if not end:
            end = self.end
            year,month,day = end.split(datesep)
            end = dt.date(int(year),int(month),int(day))
        if not weekdays:
            weekdays = self.weekdays
        if not freq:
            freq = self.freq
        # Create holder for meeting dates
        meetdates = np.empty((1,len(weekdays)),dtype=dt.date)
        for d,day in enumerate(weekdays):
            if start.weekday() in weekdays:
                meetdates[d] = start
            elif start.weekday() not in weekdays:
                # Calculate how far we are from the first meeting
                ndays_away = (day - start.weekday())%7
                days_delta = dt.timedelta(days=int(ndays_away))
                meetdates[d] = start+days_delta
        # Add meeting dates until you hit the end date
        while np.max(meetdates)<end:
            meetdates = np.append(meetdates,
                                  meetdates[-1]+dt.timedelta(days=freq*7))
        meetdates = meetdates.flatten()
        # Double check to force only dates in the range
        meetdates = meetdates[meetdates <= end]
        meetdates = np.sort(meetdates)
        return meetdates


    def random_assignment(self,pavail,navail,pstatus,nstatus,npresent=2,
                          nnote=2,interval=2,):
        """
        Function that chooses attendees randomly. pavail, navail, pstatus,
        nstatus are all number of meetings by number of participants, with
        the following status codes.

        pavail/navail:
        1   =   required
        0   =   available
        -1  =   not available

        pstatus/nstatus
        0   =   not presenting/notetaking
        1   =   presenting/notetaking


        pavail:     presentation availability for participants
        navail:     notetaking availability for participants
        pstatus:    presentation status for participants
        nstatus:    notetaking availability for participants
        npresent:   number of presenters per meeting
        nnote:      number of notetakers per meeting
        interval:   number of meetings before someone can repeat

        Returns updated pstatus, nstatus arrays
        """
        # Calculate the maximum number of times any given person should present
        pmax = np.ceil(len(self.meetdates)*npresent/self.npresenters)
        nmax = np.ceil(len(self.meetdates)*nnote/self.nnoters)
        # Store input availabilities so you can update them to avoid repeats
        masterpavail = pavail
        masternavail = navail

        # Cycle through all dates to find presenters first
        for d,date in enumerate(pstatus):
            # First check whether more presenters are needed
            if np.sum(date)<npresent:
                # Calculate the number of presenters needed
                remaining = int(npresent-np.sum(date))
                # Determine who's available
                available = np.arange(len(date),dtype=int)[pavail[d]==0]
                # If not enough people are available (because of repetition
                # restrictions), shake things up
                if available.size<npresent:
                    # Find everyone who could conceivably present
                    possavail = np.arange(len(date),dtype=int)[masterpavail[d]==0]
                    newavail = []
                    for a,avail in enumerate(possavail):
                        # Determine the interval to last presentation
                        inters = np.fabs(d-np.where(pstatus[:,avail]==1)[0])
                        if np.sum(inters<=interval)==0:
                            newavail.append(avail)
                    newavail=np.array(newavail)
                # If people are available, select them randomly
                elif available.size>=npresent:
                    chosen = np.random.choice(available,size=remaining,replace=False)
                # Update the chosen presenters' status to presenting
                pstatus[d][chosen]=1
                # Pad to ensure that there won't be repeat presentations
                padb = np.max([0,d-interval])
                padt = np.min([d+interval+1,len(pstatus)])
                padinds = np.arange(padb,padt)
                for p,pad in enumerate(padinds):
                    for c,choice in enumerate(chosen):
                        if pavail[pad][choice]!=1:
                            pavail[pad][choice]=-1
                # Update their availability and recuse them from notetaking
                pavail[d][chosen]=1
                navail[d][chosen]=-1
                # If anyone has already presented the max number of times,
                # make them unavailable (this does not override requested dates)
                reqsmet = np.where(np.sum(pstatus,axis=0)>=pmax)[0]
                datesleft = np.arange(len(self.meetdates))[d+1:]
                for r,remain in enumerate(datesleft):
                    for p,person in enumerate(reqsmet):
                        if pavail[remain][person]!=1:
                            pavail[remain][person]=-1

        # Similar to above but for notetaking - note its not identical, as the 
        # loop above updates the the notetaker availability used in this loop
        for d,date in enumerate(nstatus):
            # Check whether more notetakers are needed
            if np.sum(date)<nnote:
                # Calculate the number of missing notetakers
                remaining = int(nnote-np.sum(date))
                available = np.arange(len(date))[navail[d]==0]
                # If there aren't enough notetakers, shake things up
                if available.size<nnote:
                    possavail = np.arange(len(date),dtype=int)[masternavail[d]==0]
                    newavail = []
                    for a,avail in enumerate(possavail):
                        inters = np.fabs(d-np.where(nstatus[:,avail]==1)[0])
                        if np.sum(inters<=interval)==0:
                            newavail.append(avail)
                    newavail=np.array(newavail)
                # If there are enough notetakers, choose randomly
                elif available.size>=nnote:
                    chosen = np.random.choice(available,size=remaining,replace=False)
                # Update selected notetakers status
                nstatus[d][chosen]=1
                # Pad status to avoid repeated notetakers
                padb = np.max([0,d-interval])
                padt = np.min([d+interval+1,len(pstatus)])
                padinds = np.arange(padb,padt)
                for p,pad in enumerate(padinds):
                    for c,choice in enumerate(chosen):
                        if navail[pad][choice]!=1:
                            navail[pad][choice]=-1
                # Update availability
                navail[d][chosen]=1
                reqsmet = np.where(np.sum(nstatus,axis=0)>=pmax)[0]
                datesleft = np.arange(len(self.meetdates))[d+1:]
                for r,remain in enumerate(datesleft):
                    for p,person in enumerate(reqsmet):
                        if navail[remain][person]!=1:
                            navail[remain][person]=-1
        return pstatus,nstatus


    def populate_schedule(self,npresent=2,nnote=2,interval=2,**kwargs):
        """
        Creates matrices to summarize the availability of all participants
        for notetaking and presenting.

        npresent:   number of presenters per meeting
        nnote:      number of notetakers per meeting
        interval:   number of meetings before someone can repeat

        Returns None

        """
        # read availability

        np.random.seed(self.seed)
        # set meetdates (array)

        # These arrays have three statuses:
        #  1    =   required
        #  0    =   available 
        # -1    =   not available
        pavail = np.zeros((len(self.meetdates),len(self.people_list)),dtype=int)
        navail = np.zeros((len(self.meetdates),len(self.people_list)),dtype=int)

        # Check each person for dates they cannot present and must present.
        # Update their availability accordingly, then make sure they will not
        # present too soon after one of their required dates.
        for p,person in enumerate(self.people_list):
            forbidden = read_datelist(self.people[person].forbid,
                                      self.meetdates,**kwargs)
            forced =  read_datelist(self.people[person].force,
                                    self.meetdates,**kwargs)
            badmeets = np.in1d(self.meetdates,forbidden)
            goodmeets = np.in1d(self.meetdates,forced)
            padded_badmeets = badmeets
            forced_meets = np.where(goodmeets)[0]
            # Add forbidden dates adjacent to required presentations
            for f,force in enumerate(forced_meets):
                start = np.max([0,force-interval])
                end = np.min([force+interval+1,len(self.meetdates)])
                padded_badmeets[start:end]=True
            # Add flags for presenting
            if self.people[person].talk:
                # Note that this ordering means force will always override interval padding
                pavail[:,p][badmeets] = -1
                pavail[:,p][goodmeets] = 1
            elif not self.people[person].talk:
                pavail[:,p] = -1
            # Add flags for notetaking
            if self.people[person].notes:
                # Can't take notes if you're presenting (ideally)
                navail[:,p][badmeets] = -1
                navail[:,p][goodmeets] = -1
            elif not self.people[person].notes:
                navail[:,p] = -1

        # Initialize status arrays
        pstatus = np.zeros((len(self.meetdates),len(self.people_list)),dtype=int)
        nstatus = np.zeros((len(self.meetdates),len(self.people_list)),dtype=int)

        # Update status arrays to accomodate dates with required presenters
        pstatus[pavail==1] = 1

        # Find random presentation schedule
        pstatus,nstatus = self.random_assignment(pavail,navail,pstatus,nstatus,
                                                 npresent=npresent,nnote=nnote,
                                                 interval=interval)
        self.pstatus=pstatus
        self.nstatus=nstatus

    def show_schedule(self):
        """
        Prettify the schedule and print to console. Save a copy to file
        for reference.
        Return None.
        """
        fname = f'schedule_{self.start}_{self.end}.txt'
        with open(fname,'w') as f:
            for d,date in enumerate(self.meetdates):
                presenters = self.names[self.pstatus[d]==1]
                noters = self.names[self.nstatus[d]==1]
                dateinfo = f'{date}\npresenters:{[p for p in presenters]}\nnotetakers:{[n for n in noters]}'
                f.write(dateinfo+'\n')
                print(dateinfo)
            ptotals = np.sum(self.pstatus,axis=0)
            ntotals = np.sum(self.nstatus,axis=0)

            # Print overall stats
            for p,person in enumerate(self.people_list):
                statinfo = f'{self.names[p]} presented {ptotals[p]} times, took notes {ntotals[p]} times'
                f.write(statinfo+'\n')
                print(statinfo)
            f.close()



if __name__=='__main__':

    arguments = docopt(__doc__)
    start = arguments['--start']
    end = arguments['--end']
    weekdays = arguments['--week']
    const = arguments['--cnstrt']

    # Read constraints file

    constraints = read_constraints(const)
    forbid = constraints['FORBID']
    people = constraints['PEOPLE'].split(',')

    # If dates are not given in arguments, use file versions. if dates
    # are not given in constraint files, make assumptions and warn
    if start=='None':
        try:
            start = constraints['START'].strip()
        except KeyError:
            warnings.warn('No start date specified, assuming today is start date')
            start = dt.date.today()
    if end=='None':
        try:
            end = constraints['END'].strip()
        except KeyError:
            warnings.warn('No end date specified, producing results for one month')
            end = dt.date.today()+dt.timedelta(days=30)

    if weekdays=='None':
        try:
            weekdays = constraints['WEEK'].split(',')
        except KeyError:
            warnings.warn('No weekday(s) specified, assuming today is meeting day')
            weekdays = [dt.date.today().weekday()]

    s = schedule(start,end,weekdays,forbid,people,seed=9)
    s.populate_schedule()
    s.show_schedule()
